"""신규 합성 글의 모델 응답을 행사·일자·좌석·장당 가격 정답과 비교한다."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.extractor import extract_with_llm
from src.privacy import require_demo_safe

FIELDS = ("event_name", "event_date", "seat_grade", "asking_price_krw")


def evaluate(cases):
    model = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "mode": "live",
              "model": model, "total": len(cases), "attempts": 0, "valid_responses": 0, "rows": []}
    for case in cases:
        require_demo_safe(case["text"])
        if set(case["gold"]) != set(FIELDS):
            raise ValueError("모든 필드의 정답 또는 null을 명시해야 합니다.")
    if not os.environ.get("OPENAI_API_KEY"):
        report["status"] = "blocked_missing_credentials"
        return report
    for case in cases:
        row = {"id": case["id"], "gold": case["gold"]}
        report["attempts"] += 1
        try:
            answer = extract_with_llm(case["text"], model=model)
            row["actual"] = {f: answer[f] for f in FIELDS}
            row["matches"] = {f: answer[f] == case["gold"][f] for f in FIELDS}
            row["evidence"] = answer["evidence_phrases"]
            report["valid_responses"] += 1
        except ValueError as exc:
            row["error"] = str(exc)
        report["rows"].append(row)
    report["status"] = "finished" if report["valid_responses"] == len(cases) else "partial_or_failed"
    if report["status"] == "finished":
        report["exact_by_field"] = {field: sum(r["matches"][field] for r in report["rows"]) for field in FIELDS}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = json.loads((Path(__file__).with_name("novel_posts.json")).read_text(encoding="utf-8"))
    result = evaluate(cases)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if result["status"] == "finished" else 2)
