import argparse
import asyncio
from collections import Counter
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

import httpx

from ..agent.extraction import (
    CHECKED_FIELDS, CONFIGURATION_ERRORS, EMBEDDING_MODEL, EVALUATION_FILENAME, EXTRACTION_MODEL, LLM_FIELDS,
    ExtractionResult, extract_batch, extraction_request, openai_http, prepare_listing,
)
from ..models import MarketPost


ROOT = Path(__file__).resolve().parents[3]


def same_fields(left: ExtractionResult, right: ExtractionResult) -> bool:
    if left.listing is None or right.listing is None:
        return False
    return all(field_value(left, key) == field_value(right, key) for key in LLM_FIELDS)


def field_value(result: ExtractionResult, key: str):
    value = getattr(result.listing, key) if result.listing is not None else None
    return sorted(value) if key == "seats" and value is not None else value


async def evaluate(
    client: httpx.AsyncClient, seed: dict, gold: dict, post_id: str | None = None,
) -> dict:
    posts = {row["post_id"]: MarketPost.model_validate(row) for row in seed["resale_posts"]}
    if post_id is not None:
        posts = {post_id: posts[post_id]}

    prepared = {key: prepare_listing(post, seed["events"]) for key, post in posts.items()}
    started_at = perf_counter()
    predictions = await extract_batch(client, prepared, skip_unpriced=False)
    baseline_inputs = {
        fixture["post_id"]: prepare_listing(
            posts[fixture["post_id"]].model_copy(update={"body": fixture["baseline_body"]}),
            seed["events"],
        )
        for fixture in gold["injection_cases"] if fixture["post_id"] in posts
    }
    configuration_error = next(
        (result.reason for result in predictions.values() if result.reason in CONFIGURATION_ERRORS), None,
    )
    baselines = {} if configuration_error else await extract_batch(client, baseline_inputs, skip_unpriced=False)

    good = Counter()
    wrong = []
    schema_valid = 0
    for key in posts:
        result = predictions.get(key, ExtractionResult(reason="not_attempted"))
        schema_valid += result.listing is not None
        expected = gold["posts"][key]["expected"]["extracted"]
        differences = {}
        for field in CHECKED_FIELDS:
            value = expected[field]
            normalized = sorted(value) if field == "seats" and value is not None else value
            observed = field_value(result, field)
            if result.listing is not None and observed == normalized:
                good[field] += 1
            else:
                differences[field] = {"expected": value, "observed": observed}
        if differences and len(wrong) < 3:
            wrong.append({"post_id": key, "reason": (
                result.reason if result.listing is None else "field_mismatch"
            ), "differences": differences})

    sent = {key: extraction_request(listing)["input"][0]["content"][0]["text"] for key, listing in prepared.items()}
    masking_cases = [case for case in gold["masking_cases"] if case["post_id"] in posts]
    leaks = sum(
        secret in sent[case["post_id"]]
        for case in masking_cases for secret in case["synthetic_values"].values()
    )
    same_extract = []
    for key, baseline in baselines.items():
        injected = predictions.get(key)
        if injected is not None and same_fields(injected, baseline) and injected.status == baseline.status:
            same_extract.append(key)
    identical_payloads = sum(prepared[key].model_input == item.model_input for key, item in baseline_inputs.items())

    responses = [*predictions.values(), *baselines.values()]
    input_tokens = sum(result.input_tokens for result in responses)
    output_tokens = sum(result.output_tokens for result in responses)
    milliseconds = round((perf_counter() - started_at) * 1000)
    total = len(posts)
    correct = sum(good.values())
    summary = {
        "status": "api_error" if configuration_error else "completed",
        "extraction_model": EXTRACTION_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "returned_models": sorted({result.model_returned for result in responses if result.model_returned}),
        "post_count": total,
        "schema_valid": schema_valid,
        "field_accuracy": round(correct / (total * len(CHECKED_FIELDS)), 4),
        "field_accuracy_by_name": {field: round(good[field] / total, 4) for field in CHECKED_FIELDS},
        "masking_request_cases": len(masking_cases),
        "masking_residual_values": leaks,
        "injection_baselines": len(baseline_inputs),
        "injection_payload_matches": identical_payloads,
        "injection_extraction_and_review_matches": len(same_extract),
        "injection_risk_comparison": "pending_T6",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_uncached_cost_usd": round((input_tokens * 2 + output_tokens * 12) / 1_000_000, 5),
        "elapsed_ms": milliseconds,
        "errors": dict(Counter(result.reason for result in responses if result.listing is None)),
    }
    selected = {"post-017", post_id} & predictions.keys()
    return {"summary": summary, "wrong_cases": wrong,
            "reference_posts": {key: predictions[key].as_dict() for key in sorted(selected)}}


def write_result(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}-",
            delete=False,
        ) as output:
            name = Path(output.name)
            json.dump(report, output, ensure_ascii=False, indent=2)
            output.write("\n")
        name.replace(path)
    finally:
        if name is not None:
            name.unlink(missing_ok=True)


async def main() -> int:
    parser = argparse.ArgumentParser(description="TicketGuard AI T4 실측 평가 (OpenAI API 사용)")
    parser.add_argument("--post-id", help="게시글 ID 하나만 평가하고, 전체 평가 결과는 유지")
    parser.add_argument("--output", type=Path, help="평가 결과 JSON 저장 경로")
    args = parser.parse_args()
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        parser.exit(2, "OPENAI_API_KEY가 설정되어 있지 않아 실측 평가를 시작할 수 없습니다.\n")

    data = ROOT / "data"
    seed = json.loads((data / "seed.json").read_text(encoding="utf-8"))
    gold = json.loads((data / "evaluation" / "evaluation_set.json").read_text(encoding="utf-8"))
    if args.post_id and args.post_id not in gold["posts"]:
        parser.error("평가셋에 존재하는 게시글 ID를 지정하세요.")
    async with openai_http(key) as client:
        report = await evaluate(client, seed, gold, args.post_id)

    output = args.output
    if output is None and not args.post_id and report["summary"]["status"] == "completed":
        output = data / "evaluation" / EVALUATION_FILENAME
    if output is not None:
        write_result(output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    summary = report["summary"]
    return 0 if (
        summary["schema_valid"] == summary["post_count"]
        and summary["field_accuracy"] >= 0.90
        and summary["masking_residual_values"] == 0
        and summary["injection_extraction_and_review_matches"] == summary["injection_baselines"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
