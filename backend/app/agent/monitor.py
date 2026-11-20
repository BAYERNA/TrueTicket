from collections import Counter
import json
from time import perf_counter
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ..adapters.resale_monitor import collect_posts
from ..models import MarketPost
from ..services.analysis import LEADS, add_bot_evidence, assess_risk, cluster_seller, explain, match_booking, style_text
from .extraction import prepare_listing
from .gemini import AIUnavailable, Gemini, fingerprint, service_interrupted
from .local import extract_local
from .pii import mask_pii


class MonitorState(TypedDict, total=False):
    run_id: str
    event_id: str | None
    mode: str
    posts: tuple[MarketPost, ...]
    prepared: dict
    records: dict
    events: list[dict]
    summary: dict


def build_monitor(db, feed_port: int, ai: Gemini | None = None):
    ai = ai or Gemini(db)

    def log(state, step, tool, summary, started):
        db.record_agent_step(state["run_id"], state.get("event_id"), step, tool, summary,
                             round((perf_counter() - started) * 1000))

    async def collect(state):
        started = perf_counter()
        collected = await collect_posts(state.get("event_id"), feed_port=feed_port)
        summary = {"status": collected.status, "post_count": len(collected.posts),
                   "post_ids": [p.post_id for p in collected.posts], "error": collected.error,
                   "http_status": collected.http_status, "mode": state["mode"]}
        log(state, "collect", "collect_posts", summary, started)
        return {"posts": collected.posts, "summary": summary}

    def mask(state):
        started = perf_counter()
        events = db.list_events()
        prepared = {p.post_id: prepare_listing(p, events) for p in state["posts"]}
        counts = Counter()
        for item in prepared.values():
            counts.update(item.masked_counts)
        log(state, "mask", "mask_pii", {"posts": len(prepared), "masked_counts": dict(counts)}, started)
        return {"events": events, "prepared": prepared}

    async def extract(state):
        started = perf_counter()
        previous = db.read_extractions() if state["mode"] == "gemini" else {}
        results = {}
        error = None
        for post_id, item in state["prepared"].items():
            if state["mode"] == "local":
                results[post_id] = extract_local(item)
            elif previous.get(post_id, {}).get("fingerprint") == fingerprint(item) and previous[post_id].get("schema_valid"):
                results[post_id] = {**previous[post_id], "source": "cache", "input_tokens": 0, "output_tokens": 0}
            else:
                results[post_id] = await ai.extract(item)
                reason = results[post_id].get("reason")
                if service_interrupted(reason):
                    error = reason
                    break
                if results[post_id]["schema_valid"]:
                    db.cache_gemini_extraction(post_id, results[post_id])
        summary = {"status": "failed" if error else "completed", "processed": len(results),
                   "ready": sum(r["status"] == "extracted" for r in results.values()),
                   "review": sum(r["status"] == "review" for r in results.values()),
                   "cached": sum(r["source"] == "cache" for r in results.values()),
                   "provider": state["mode"], "api_requests": ai.requests, "error": error}
        log(state, "extract", "extract_listing", summary, started)
        if error:
            return {"summary": {**state["summary"], "extraction": summary}}
        records = {}
        for post in state["posts"]:
            item = state["prepared"][post.post_id]
            records[post.post_id] = {"post": {**post.model_dump(), "title": item.title, "body": item.body,
                                              "author_handle": mask_pii(post.author_handle).text},
                                     "masked_body": item.body, "extraction": results[post.post_id],
                                     "slang": item.slang}
        return {"records": records, "summary": {**state["summary"], "extraction": summary}}

    def match(state):
        started = perf_counter()
        with db.connect() as connection:
            for record in state["records"].values():
                record["match"] = match_booking(connection, record["extraction"])
        log(state, "match", "match_booking", {
            "matched_posts": sum(bool(r["match"]["bookings"]) for r in state["records"].values()),
            "failures": dict(Counter(r["match"]["failure_reason"] for r in state["records"].values() if r["match"]["failure_reason"])),
        }, started)
        return {"records": state["records"]}

    def score(state):
        started = perf_counter()
        for record in state["records"].values():
            add_bot_evidence(record["match"])
        log(state, "bot_score", "bot_score", {"bookings": sum(len(r["match"]["bookings"]) for r in state["records"].values())}, started)
        return {"records": state["records"]}

    async def cluster(state):
        started = perf_counter()
        vectors = {}
        if state["mode"] == "gemini":
            try:
                vectors = await ai.embed({key: style_text(r["masked_body"]) or r["masked_body"]
                                          for key, r in state["records"].items()})
            except AIUnavailable as unavailable:
                error = str(unavailable)
                log(state, "cluster", "cluster_seller", {"status": "failed", "error": error}, started)
                return {"summary": {**state["summary"], "cluster_error": error}}
        clusters = cluster_seller(state["records"], vectors, author_handles={p.post_id: p.author_handle for p in state["posts"]})
        for key, record in state["records"].items():
            record["cluster"] = clusters[key]
        log(state, "cluster", "cluster_seller", {
            "clusters": len({c["cluster_id"] for c in clusters.values()}),
            "method": "gemini_embedding_and_rules" if vectors else "local_rules", "error": None,
        }, started)
        return {"records": state["records"]}

    async def assess(state):
        started = perf_counter()
        events = {event["id"]: event for event in state["events"]}
        for record in state["records"].values():
            record["risk"] = assess_risk(record, state["records"], record["cluster"], events)
        lead = None
        generation_error = None
        if state["mode"] == "gemini" and state["records"]:
            try:
                text, _ = await ai.structured(
                    "규칙 엔진의 검토 결과를 소개하는 문장을 주어진 lead 중 하나로 선택한다. 사실이나 판단을 추가하지 않는다.",
                    json.dumps({"risk_counts": dict(Counter(r["risk"]["risk_level"] for r in state["records"].values()))}, ensure_ascii=False),
                    {"type": "object", "properties": {"lead": {"type": "string", "enum": list(LEADS)}},
                     "required": ["lead"], "additionalProperties": False},
                )
                candidate = json.loads(text).get("lead")
                lead = candidate if candidate in LEADS else None
                if lead is None:
                    generation_error = "invalid_explanation"
            except (AIUnavailable, ValueError, AttributeError) as error:
                generation_error = str(error) if isinstance(error, AIUnavailable) else "invalid_explanation"
        for record in state["records"].values():
            record["explanation"] = explain(record["risk"], lead)
        db.save_analyses(state["records"])
        summary = {"cases": len(state["records"]),
                   "risks": dict(Counter(r["risk"]["risk_level"] for r in state["records"].values())),
                   "mode": state["mode"], "api_requests": ai.requests,
                   "input_tokens": ai.input_tokens, "output_tokens": ai.output_tokens,
                   "explanation_source": "gemini_constrained_template" if lead else "rule_template",
                   "status": "partial" if generation_error else "completed",
                   "error": generation_error, "generation_error": generation_error}
        log(state, "assess", "assess_risk", summary, started)
        return {"summary": {**state["summary"], **summary}}

    graph = StateGraph(MonitorState)
    nodes = {"collect": collect, "mask": mask, "extract": extract, "match": match,
             "bot_score": score, "cluster": cluster, "assess": assess}
    for name, node in nodes.items():
        graph.add_node(name, node)
    graph.add_edge(START, "collect")
    graph.add_conditional_edges("collect", lambda s: "mask" if s["summary"]["status"] == "ok" else END)
    graph.add_edge("mask", "extract")
    graph.add_conditional_edges("extract", lambda s: END if s["summary"]["extraction"]["error"] else "match")
    graph.add_edge("match", "bot_score")
    graph.add_edge("bot_score", "cluster")
    graph.add_conditional_edges("cluster", lambda s: END if s["summary"].get("cluster_error") else "assess")
    graph.add_edge("assess", END)
    return graph.compile()
