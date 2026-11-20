from hashlib import sha256
import math
import re

from ..adapters.bot_detection import bot_score
from ..agent.extraction import MIN_CONFIDENCE


RULES = {
    "R1": {"label": "구입가 초과", "description": "장당 판매가가 정가와 예매 수수료의 합계보다 높습니다."},
    "R2": {"label": "2장 이상 초과 판매", "description": "같은 판매자 후보의 구입가 초과 좌석이 중복을 제외하고 2개 이상입니다."},
    "R3": {"label": "정가 2배 이상", "description": "장당 판매가가 해당 좌석 정가의 2배 이상입니다."},
    "R4": {"label": "부정구매 의심", "description": "연결된 예매의 봇 점수가 0.8 이상입니다."},
    "R5": {"label": "사기 신호", "description": "거래 조건이나 가격에서 사기 의심 신호가 발견됐습니다."},
}
FAILURES = {
    "missing_seats": "좌석 정보 없음", "unknown_event": "공연·회차 확인 불가",
    "seat_not_found": "없는 좌석", "cancelled_booking": "취소된 예매",
    "quantity_mismatch": "수량과 좌석 수 불일치", "low_confidence": "추출 신뢰도 부족",
    "missing_price": "가격 정보 없음", "missing_quantity": "유효한 판매 수량 없음",
}
LEADS = ("확인된 근거를 바탕으로 운영자 검토가 필요합니다.", "기록된 신호를 확인하고 소명 절차를 검토하세요.")


def match_booking(connection, result: dict) -> dict:
    fields = result.get("fields") or {}
    seats = fields.get("seats") or []
    reason = None
    if not seats:
        reason = "missing_seats"
    elif result.get("reason") == "missing_quantity":
        reason = "missing_quantity"
    elif result.get("status") != "extracted":
        reason = "missing_price" if fields.get("price_per_ticket_krw") is None else "low_confidence"
    elif not fields.get("event_id") or not fields.get("session_id"):
        reason = "unknown_event"
    elif fields["confidence"]["seats"] < MIN_CONFIDENCE:
        reason = "low_confidence"
    elif fields.get("quantity") is not None and fields["quantity"] != len(seats):
        reason = "quantity_mismatch"
    if reason:
        return {"matched_booking_ids": [], "bookings": [], "failure_reason": reason}
    bookings = []
    for seat in seats:
        row = connection.execute(
            "SELECT b.*, a.nickname FROM bookings b JOIN accounts a USING(account_id) "
            "WHERE b.event_id = ? AND b.session_id = ? AND b.seat = ?",
            (fields["event_id"], fields["session_id"], seat),
        ).fetchone()
        if row is None:
            return {"matched_booking_ids": [], "bookings": [], "failure_reason": "seat_not_found"}
        booking = dict(row)
        if booking["status"] != "confirmed":
            return {"matched_booking_ids": [], "bookings": [], "failure_reason": "cancelled_booking"}
        bookings.append(booking)
    return {"matched_booking_ids": sorted(b["booking_id"] for b in bookings),
            "bookings": bookings, "failure_reason": None}


def add_bot_evidence(match: dict) -> dict:
    for booking in match["bookings"]:
        events = booking.pop("behavior_events")
        if isinstance(events, str):
            import json
            events = json.loads(events)
        booking["bot"] = bot_score(events)
    return match


def style_text(body: str) -> str:
    # Retain prose after the pricing/seat sentences, excluding short generic trade phrases.
    sentences = re.split(r"[.!?。\n]+", body)
    prose = [s.strip() for s in sentences if len(s.strip()) >= 12 and not re.search(
        r"\d|[RS]석|정가|원에|만원|계좌|이메일|연락처|\[.*\]", s,
    )]
    return " ".join(prose[-2:])


def cosine(a: list[float], b: list[float]) -> float:
    denominator = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b, strict=True)) / denominator if denominator else 0.0


def cluster_seller(records: dict[str, dict], vectors: dict[str, list[float]] | None = None,
                   *, author_handles: dict[str, str] | None = None) -> dict[str, dict]:
    vectors = vectors or {}
    if author_handles is None:
        author_handles = {key: item["post"]["author_handle"] for key, item in records.items()}
    keys = sorted(records)
    parent = {key: key for key in keys}
    links = []

    def root(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for index, left_key in enumerate(keys):
        left = records[left_key]
        for right_key in keys[index+1:]:
            right = records[right_key]
            if left["post"]["event_id"] != right["post"]["event_id"]:
                continue
            same_author = author_handles[left_key] == author_handles[right_key]
            left_style = style_text(left["masked_body"])
            right_style = style_text(right["masked_body"])
            same_style = bool(len(left_style) >= 18 and left_style == right_style)
            similarity = cosine(vectors[left_key], vectors[right_key]) if left_key in vectors and right_key in vectors else None
            # Semantic similarity alone can group unrelated fans of the same performance.
            # Require corroborating repeated prose or an exact local author handle.
            if same_author or (same_style and (similarity is None or similarity >= 0.85)):
                parent[root(right_key)] = root(left_key)
                links.append({"left": left_key, "right": right_key,
                              "reason": "same_author" if same_author else "repeated_trade_prose",
                              "similarity": round(similarity, 4) if similarity is not None else None})
    groups: dict[str, list[str]] = {}
    for key in keys:
        groups.setdefault(root(key), []).append(key)
    clusters = {}
    for members in groups.values():
        cluster_id = "cluster-" + sha256("|".join(members).encode()).hexdigest()[:12]
        evidence = [link for link in links if link["left"] in members and link["right"] in members]
        for key in members:
            clusters[key] = {"cluster_id": cluster_id, "post_ids": members,
                             "method": "gemini_embedding_and_rules" if vectors else "local_rules",
                             "evidence": evidence}
    return clusters


def sale_exceeds_purchase(record: dict) -> bool:
    price = (record["extraction"].get("fields") or {}).get("price_per_ticket_krw")
    bookings = record["match"]["bookings"]
    return price is not None and bool(bookings) and any(price > b["price_paid"] for b in bookings)


def assess_risk(record: dict, records: dict[str, dict], cluster: dict, events: dict[str, dict]) -> dict:
    extraction = record["extraction"]
    fields = extraction.get("fields") or {}
    confidence = fields.get("confidence") or {}
    if extraction["status"] != "extracted" or not fields.get("seats") or min(
        confidence.get("price_per_ticket_krw", 0), confidence.get("seats", 0),
    ) < MIN_CONFIDENCE:
        return {"risk_level": "확인 불가", "rule_hits": [], "evidence": {}, "above_cost_seat_count": 0}
    event = events.get(fields.get("event_id"))
    if event is None:
        return {"risk_level": "확인 불가", "rule_hits": [], "evidence": {}, "above_cost_seat_count": 0}
    price = fields["price_per_ticket_krw"]
    bookings = record["match"]["bookings"]
    unique_seats = {
        (booking["event_id"], booking["session_id"], booking["seat"])
        for post_id in cluster["post_ids"] if sale_exceeds_purchase(records[post_id])
        for booking in records[post_id]["match"]["bookings"]
        if records[post_id]["extraction"]["fields"]["price_per_ticket_krw"] > booking["price_paid"]
    }
    r1 = sale_exceeds_purchase(record)
    bot = max((b["bot"]["score"] for b in bookings), default=0.0)
    body = record["masked_body"]
    fraud = bool(
        re.search(r"선입금", body) and re.search(r"아옮|직링", body)
        or re.search(r"추가로.*입금|추가\s*입금|입금자명.*바꿔|입금자명.*변경", body)
    )
    face_values = [event["seat_grades"][b["grade"]] for b in bookings]
    below_market = bool(face_values and price < min(face_values) * 0.5)
    hits = [key for key, condition in (
        ("R1", r1), ("R2", r1 and len(unique_seats) >= 2),
        ("R3", bool(face_values) and price >= min(face_values) * 2),
        ("R4", bot >= 0.8), ("R5", fraud or below_market),
    ) if condition]
    risk = "낮음"
    if "R4" in hits or ("R1" in hits and bool({"R2", "R3"} & set(hits))):
        risk = "높음"
    elif "R1" in hits or "R5" in hits:
        risk = "중간"
    elif record["match"]["failure_reason"]:
        risk = "확인 불가"
    evidence = {
        "R1": {"sale_price": price, "purchase_prices": [b["price_paid"] for b in bookings]},
        "R2": {"unique_seats": len(unique_seats), "post_ids": cluster["post_ids"]},
        "R3": {"sale_price": price, "face_prices": face_values},
        "R4": {"max_bot_score": bot, "threshold": 0.8},
        "R5": {"advance_transfer_or_extra_payment": fraud, "below_half_face_price": below_market},
    }
    return {"risk_level": risk, "rule_hits": hits,
            "evidence": {key: evidence[key] for key in hits}, "above_cost_seat_count": len(unique_seats)}


def explain(risk: dict, lead: str | None = None) -> dict:
    hits = risk["rule_hits"]
    sentences = [{"rule_id": key, "text": RULES[key]["description"]} for key in hits]
    if not hits:
        text = "현재 확인된 규칙 신호가 없습니다." if risk["risk_level"] == "낮음" else "가격·좌석·예매 정보를 추가로 확인해야 합니다."
    else:
        text = " ".join(sentence["text"] for sentence in sentences)
    used_ai = lead in LEADS and bool(hits)
    if used_ai:
        text = lead + " " + text
    return {"text": text, "sentences": sentences, "rule_ids": hits,
            "generated_by_ai": used_ai, "source": "gemini_constrained_template" if used_ai else "rule_template"}
