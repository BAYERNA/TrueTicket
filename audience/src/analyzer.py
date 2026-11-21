from decimal import ROUND_HALF_UP, Decimal

from .privacy import require_demo_safe
from .repository import find_event, get_grounding


def source_label(row):
    if row is None:
        return None
    kind = "가상 시연 자료" if row["is_demo"] else "등록 출처"
    return f"{kind} · {row['source_title']} · {row['ref_id']} · {row['retrieved_on']}"


def analyze(extracted, conn, text):
    require_demo_safe(text)
    quotes = [p for p in extracted.get("evidence_phrases", []) if p in text]
    facts = [f"글에 적힌 문구  “{q}”" for q in quotes]
    signals = []
    unknowns = ["글쓴이의 실제 구입가와 할인 여부", "티켓 소유권, 판매처 동의, 상습·영업 여부"]
    actions = ["송금 전에 주최사나 공식 예매처에서 양도 및 입장 조건을 확인하세요."]
    report = {
        "level": "INSUFFICIENT",
        "facts": facts,
        "signals": signals,
        "unknowns": unknowns,
        "actions": actions,
        "benchmark_source": None,
        "policy_source": None,
        "premium_pct_vs_list": None,
        "premium_krw": None,
        "list_price_krw": None,
        "asking_price_krw": extracted.get("asking_price_krw"),
        "legal_verdict": "NOT_DETERMINED",
        "extraction_mode": extracted.get("extraction_mode"),
    }
    event = find_event(
        conn, extracted.get("event_name"), extracted.get("category"), extracted.get("event_date")
    )
    if event is None:
        unknowns.append("등록 정보와 일치하는 행사 또는 회차를 찾을 수 없습니다.")
        return report

    name = event["name"]
    facts.append(f"가상 행사 목록  {name} · {event['event_date']}")
    price, policy = get_grounding(conn, event["id"], extracted.get("seat_grade"))
    asking = report["asking_price_krw"]
    valid_asking = type(asking) is int and 0 <= asking <= 9_000_000_000
    report["benchmark_source"], report["policy_source"] = source_label(price), source_label(policy)
    if price is not None:
        listed = price["list_price_krw"]
        report["list_price_krw"] = listed
        facts.append(f"{price['seat_grade']}석 기준가 {listed:,}원 · {price['source_id']}")
    if valid_asking and price is not None:
        difference = asking - listed
        report["premium_krw"] = difference
        facts.append(f"장당 제시액 {asking:,}원 · 기준가 대비 차액 {difference:+,}원")
        if listed:
            pct = (Decimal(difference) * 100 / listed).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            report["premium_pct_vs_list"] = float(pct)
            facts.append(f"가상 기준가 대비 {pct:+.1f}%")
        else:
            unknowns.append("기준가가 0원이므로 초과율을 계산할 수 없습니다.")
        if difference > 0:
            signals.append(
                f"제시액이 {price['seat_grade']}석 가상 기준가보다 {difference:,}원 높습니다. 근거 {price['source_id']}."
            )
    else:
        unknowns.append("좌석 등급별 기준가 또는 장당 제시액이 부족해 차액을 확인할 수 없습니다.")

    if policy is None or policy["transfer_status"] == "UNKNOWN":
        unknowns.append("이 행사의 양도 정책을 확인할 수 없습니다.")
    else:
        status = policy["transfer_status"]
        facts.append(f"등록 정책  {policy['notes']} · {policy['source_id']}")
        if status == "PROHIBITED":
            signals.append(
                f"가상 정책상 양도가 제한되어 입장이 거절될 수 있습니다. 근거 {policy['source_id']}."
            )
        elif status == "CONDITIONAL":
            unknowns.append("공식 앱의 선물하기 등 지정된 이전 절차를 거쳤는지 확인이 필요합니다.")
    if "여러 장 보유" in text:
        signals.append("글의 “여러 장 보유” 문구는 보유 수량에 관한 작성자의 주장입니다.")
    if (
        price is not None
        and valid_asking
        and policy is not None
        and policy["transfer_status"] != "UNKNOWN"
    ):
        report["level"] = "CAUTION" if signals else "REVIEW"
    return report
