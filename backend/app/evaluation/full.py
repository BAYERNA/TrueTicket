"""Offline rule validation and explicit, opt-in Gemini measurements on private gold data."""

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from time import perf_counter

from ..agent.extraction import LLM_FIELDS, prepare_listing
from ..agent.gemini import AIUnavailable, EMBEDDING_MODEL, MODEL, Gemini, api_key, fingerprint, service_interrupted
from ..agent.local import extract_local
from ..db import Database
from ..models import MarketPost
from ..services.analysis import add_bot_evidence, assess_risk, cluster_seller, explain, match_booking, style_text
from .t4 import write_result


ROOT = Path(__file__).resolve().parents[3]
FIELDS = ("price_per_ticket_krw", "seats", "quantity")


async def evaluate(mode: str, usage_db: Database) -> dict:
    started = perf_counter()
    seed = json.loads((ROOT / "data/seed.json").read_text(encoding="utf-8"))
    gold = json.loads((ROOT / "data/evaluation/evaluation_set.json").read_text(encoding="utf-8"))
    ai = Gemini(usage_db)
    progress_path = ROOT / "data/evaluation/gemini_progress.json"
    progress = {"extractions": {}, "baselines": {}}
    if mode == "gemini" and progress_path.is_file():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    resumed = 0

    async def extract(prepared, key, section):
        nonlocal resumed
        if mode == "local":
            return extract_local(prepared)
        cached = progress[section].get(key, {})
        if cached.get("fingerprint") == fingerprint(prepared) and cached.get("schema_valid"):
            resumed += 1
            return cached
        result = await ai.extract(prepared, skip_unpriced=False)
        if result["schema_valid"]:
            progress[section][key] = {**result, "measured_at": datetime.now(timezone.utc).isoformat()}
            write_result(progress_path, progress)
        return result
    with tempfile.TemporaryDirectory(prefix="trueticket-eval-") as temporary:
        db = Database(Path(temporary) / "isolated.sqlite3", ROOT / "data/seed.json")
        db.initialize()
        posts = {p["post_id"]: MarketPost.model_validate(p) for p in seed["resale_posts"]}
        prepared = {key: prepare_listing(post, seed["events"]) for key, post in posts.items()}
        records = {}
        for key, post in posts.items():
            extraction = await extract(prepared[key], key, "extractions")
            with db.connect() as connection:
                match = add_bot_evidence(match_booking(connection, extraction))
            records[key] = {"post": post.model_dump(), "masked_body": prepared[key].body,
                            "extraction": extraction, "match": match}
            if mode == "gemini" and service_interrupted(extraction.get("reason")):
                raise AIUnavailable(extraction["reason"])
        vectors = await ai.embed({key: style_text(r["masked_body"]) or r["masked_body"] for key, r in records.items()}) if mode == "gemini" else {}
        clusters = cluster_seller(records, vectors)
        events = {e["id"]: e for e in seed["events"]}
        for key, record in records.items():
            record["cluster"] = clusters[key]
            record["risk"] = assess_risk(record, records, clusters[key], events)
            record["explanation"] = explain(record["risk"])

        good = Counter()
        wrong = []
        matched = 0
        seat_posts = 0
        for key, record in records.items():
            expected = gold["posts"][key]["expected"]
            fields = record["extraction"].get("fields") or {}
            differences = {}
            for field in FIELDS:
                observed, target = fields.get(field), expected["extracted"][field]
                if field == "seats":
                    observed = sorted(observed) if observed else None
                    target = sorted(target) if target else None
                if record["extraction"]["schema_valid"] and observed == target:
                    good[field] += 1
                else:
                    differences[field] = {"expected": target, "observed": observed}
            if fields.get("seats"):
                seat_posts += 1
                matched += record["match"]["matched_booking_ids"] == expected["matched_booking_ids"]
            if record["match"]["matched_booking_ids"] != expected["matched_booking_ids"]:
                differences["matched_booking_ids"] = {"expected": expected["matched_booking_ids"], "observed": record["match"]["matched_booking_ids"]}
            if record["risk"]["risk_level"] != expected["risk_level"]:
                differences["risk_level"] = {"expected": expected["risk_level"], "observed": record["risk"]["risk_level"]}
            if sorted(record["risk"]["rule_hits"]) != sorted(expected["rule_hits"]):
                differences["rule_hits"] = {"expected": expected["rule_hits"], "observed": record["risk"]["rule_hits"]}
            if differences and len(wrong) < 3:
                wrong.append({"post_id": key, "differences": differences})
        positives = [key for key in records if gold["posts"][key]["label"] == "부정판매 기준 충족"]
        normal = [key for key in records if gold["posts"][key]["label"] == "정가 양도"]
        seller_posts = [key for key in records if gold["posts"][key]["expected"]["seller_group_id"]]
        cluster_correct = 0
        for key in seller_posts:
            group = gold["posts"][key]["expected"]["seller_group_id"]
            target = {k for k in records if gold["posts"][k]["expected"]["seller_group_id"] == group}
            cluster_correct += set(clusters[key]["post_ids"]) == target
        masking_residual = sum(value in prepared[case["post_id"]].model_input
                               for case in gold["masking_cases"] for value in case["synthetic_values"].values())
        injection_matches = 0
        for case in gold["injection_cases"]:
            key = case["post_id"]
            source = prepare_listing(posts[key].model_copy(update={"body": case["baseline_body"]}), seed["events"])
            baseline = await extract(source, key, "baselines")
            if mode == "gemini" and service_interrupted(baseline.get("reason")):
                raise AIUnavailable(baseline["reason"])
            peer = deepcopy(records[key])
            peer["extraction"] = baseline
            peer["masked_body"] = source.body
            with db.connect() as connection:
                peer["match"] = add_bot_evidence(match_booking(connection, baseline))
            risk = assess_risk(peer, {**records, key: peer}, clusters[key], events)
            same_fields = all((baseline.get("fields") or {}).get(field) == (records[key]["extraction"].get("fields") or {}).get(field) for field in LLM_FIELDS)
            injection_matches += bool(baseline["schema_valid"] and same_fields and risk == records[key]["risk"])
        equality, plus_one, doubles = [], [], []
        for key, record in records.items():
            fields = record["extraction"].get("fields") or {}
            rows = record["match"]["bookings"]
            if not rows or fields.get("price_per_ticket_krw") is None:
                continue
            price = fields["price_per_ticket_krw"]
            if price == rows[0]["price_paid"]:
                equality.append({"post_id": key, "passes": "R1" not in record["risk"]["rule_hits"]})
            if price == rows[0]["price_paid"] + 1:
                plus_one.append({"post_id": key, "passes": "R1" in record["risk"]["rule_hits"]})
            if price == events[rows[0]["event_id"]]["seat_grades"][rows[0]["grade"]] * 2:
                doubles.append({"post_id": key, "passes": "R3" in record["risk"]["rule_hits"]})
        metrics = {
            "post_count": len(records), "schema_valid": sum(r["extraction"]["schema_valid"] for r in records.values()),
            "field_accuracy": sum(good.values()) / (len(records) * len(FIELDS)),
            "field_accuracy_by_name": {field: good[field] / len(records) for field in FIELDS},
            "seat_posts": seat_posts, "booking_match_accuracy": matched / seat_posts if seat_posts else 0,
            "positive_count": len(positives),
            "resale_detection_rate": sum(records[k]["risk"]["risk_level"] == "높음" for k in positives) / len(positives),
            "normal_count": len(normal),
            "normal_false_positive_rate": sum(records[k]["risk"]["risk_level"] == "높음" for k in normal) / len(normal),
            "seller_cluster_accuracy": cluster_correct / len(seller_posts),
            "masking_cases": len(gold["masking_cases"]), "masking_residual_values": masking_residual,
            "injection_matches": injection_matches, "injection_cases": len(gold["injection_cases"]),
            "risks": dict(Counter(r["risk"]["risk_level"] for r in records.values())),
            "matching_failures": dict(Counter(r["match"]["failure_reason"] for r in records.values() if r["match"]["failure_reason"])),
        }
        checks = {"schema_100_percent": metrics["schema_valid"] == 80,
                  "fields_90_percent": metrics["field_accuracy"] >= 0.9,
                  "booking_match_95_percent": metrics["booking_match_accuracy"] >= 0.95,
                  "seller_cluster_80_percent": metrics["seller_cluster_accuracy"] >= 0.8,
                  "detection_90_percent": metrics["resale_detection_rate"] >= 0.9,
                  "false_positive_max_5_percent": metrics["normal_false_positive_rate"] <= 0.05,
                  "masking_zero_residual": masking_residual == 0, "injection_five_matches": injection_matches == 5,
                  "r1_equal_10": len(equality) == 10 and all(x["passes"] for x in equality),
                  "r1_plus_one_3": len(plus_one) == 3 and all(x["passes"] for x in plus_one),
                  "r3_double_5": len(doubles) == 5 and all(x["passes"] for x in doubles)}
        summary = {"status": "completed", "validation_scope": "gemini_live" if mode == "gemini" else "local_rules",
                   "ai_acceptance_verified": mode == "gemini" and all(checks.values()),
                   "measured_at": datetime.now(timezone.utc).isoformat(),
                   "extraction_model": MODEL if mode == "gemini" else "local-rules-v1",
                   "embedding_model": EMBEDDING_MODEL if mode == "gemini" else None,
                   "returned_models": sorted(ai.returned_models | {r["extraction"]["model_returned"] for r in records.values() if r["extraction"].get("model_returned")}), "metrics": metrics, "checks": checks,
                   "api_requests": ai.requests, "input_tokens": ai.input_tokens, "output_tokens": ai.output_tokens,
                   "elapsed_ms": round((perf_counter() - started) * 1000), "resumed_extractions": resumed,
                   "usage_scope": "이번 실행에서 새로 전송한 API 요청·토큰과 실행 시간",
                   "note": "가상 평가셋 실측입니다. 규칙 데모 결과는 AI 모델 성능으로 사용하지 않습니다."}
        return {"summary": summary, "wrong_cases": wrong,
                "boundaries": {"r1_equal": equality, "r1_plus_one": plus_one, "r3_double": doubles},
                "reference_post": {"post_id": "post-017", "extraction": records["post-017"]["extraction"],
                                   "match": records["post-017"]["match"], "risk": records["post-017"]["risk"]}}


async def main() -> int:
    parser = argparse.ArgumentParser(description="TrueTicket 전체 평가. Gemini 실측은 --mode gemini로 명시합니다.")
    parser.add_argument("--mode", choices=("local", "gemini"), default="local")
    args = parser.parse_args()
    if args.mode == "gemini" and not api_key():
        parser.exit(2, "GEMINI_API_KEY를 실행 환경에 설정해 주세요.\n")
    from ..main import app
    app.state.db.initialize()
    try:
        report = await evaluate(args.mode, app.state.db)
    except AIUnavailable as error:
        print(json.dumps({"status": "api_error", "error": str(error)}, ensure_ascii=False))
        return 2
    scope = "gemini" if args.mode == "gemini" else "local"
    write_result(ROOT / "data/evaluation" / f"{scope}_results.json", report)
    write_result(ROOT / "data/evaluation/latest_results.json", report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if all(report["summary"]["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
