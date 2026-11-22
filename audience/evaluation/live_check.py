"""Score real completions against the four fields in the fixed synthetic evaluation set."""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
from openai import APIError, OpenAI
from src.extractor import EXTRACTION_FORMAT, INSTRUCTION, parse_extraction, request_extraction
from src.privacy import require_demo_safe

FIELDS = ("event_name", "event_date", "seat_grade", "asking_price_krw")
DATA = Path(__file__).with_name("novel_posts.json")


def loopback_endpoint(value):
    url = urlparse(value)
    if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "::1", "localhost"}
            or url.username or url.password or url.query or url.fragment or url.path.rstrip("/") != "/v1"):
        raise argparse.ArgumentTypeError("로컬 모델의 루프백 HTTP /v1 주소를 지정하세요.")
    return value


def evaluate(cases, model, local_url=None, checkpoint=None):
    local = bool(local_url)
    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "local_openai_compatible" if local else "openai_hosted",
        "model": model,
        "endpoint": local_url if local else "https://api.openai.com/v1",
        "dataset_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
        "system_prompt_sha256": hashlib.sha256(INSTRUCTION.encode()).hexdigest(),
        "response_format": EXTRACTION_FORMAT["type"],
        "total": len(cases), "attempts": 0, "model_responses": 0, "valid_responses": 0, "rows": [],
    }
    for case in cases:
        require_demo_safe(case["text"])
        if set(case["gold"]) != set(FIELDS):
            raise ValueError("모든 필드의 정답 또는 null을 명시해야 합니다.")
    key = "local-model" if local else os.getenv("OPENAI_API_KEY")
    if not key:
        report["status"] = "blocked_missing_credentials"
        return report
    timeout = 180 if local else 25
    transport = httpx.Client(timeout=timeout, trust_env=False) if local else None
    with OpenAI(api_key=key, base_url=report["endpoint"], timeout=timeout, max_retries=0, http_client=transport) as client:
        for case in cases:
            row = {"id": case["id"], "gold": case["gold"]}
            start = time.monotonic()
            report["attempts"] += 1
            try:
                reply = request_extraction(client, model, case["text"])
                report["model_responses"] += 1
                choice = reply.choices[0]
                row.update(response_id=reply.id, response_model=reply.model, finish_reason=choice.finish_reason)
                if reply.usage:
                    row["tokens"] = {"input": reply.usage.prompt_tokens, "output": reply.usage.completion_tokens}
                row["raw"] = choice.message.content or ""
                result = parse_extraction(row["raw"], case["text"])
                row["actual"] = {f: result[f] for f in FIELDS}
                row["matches"] = {f: row["actual"][f] == row["gold"][f] for f in FIELDS}
                report["valid_responses"] += 1
            except APIError as exc:
                row["transport_error"] = type(exc).__name__
                row["http_status"] = getattr(exc, "status_code", None)
            except (ValueError, TypeError, IndexError, KeyError) as exc:
                row["validation_error"] = str(exc)
            row["elapsed_s"] = round(time.monotonic()-start, 3)
            report["rows"].append(row)
            print(f'{row["id"]}: {"accepted" if "matches" in row else "failed"} ({row["elapsed_s"]}s)', file=sys.stderr, flush=True)
            if checkpoint:
                save(report, checkpoint)
    report["status"] = "finished" if report["model_responses"] == len(cases) else "partial_or_failed"
    report["end_to_end_correct_by_field"] = {
        f: sum(row.get("matches", {}).get(f, False) for row in report["rows"]) for f in FIELDS
    }
    report["all_four_correct"] = sum(all(row.get("matches", {}).get(f, False) for f in FIELDS) for row in report["rows"])
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    return report


def save(report, path):
    temporary = path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temporary.replace(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--local-url", type=loopback_endpoint)
    parser.add_argument("--model")
    args = parser.parse_args()
    if args.local_url and not args.model:
        parser.error("--local-url에는 실제 로드한 모델의 --model 이름이 필요합니다.")
    cases = json.loads(DATA.read_text(encoding="utf-8"))
    stats = evaluate(cases, args.model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini", args.local_url, args.output)
    if args.output:
        save(stats, args.output)
    print(json.dumps({k:v for k,v in stats.items() if k != "rows"}, ensure_ascii=False, indent=2))
    sys.exit(0 if stats["status"] == "finished" else 2)
