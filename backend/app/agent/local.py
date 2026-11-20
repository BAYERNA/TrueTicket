"""Transparent rule baseline for a key-free demonstration, independent of gold labels."""

from decimal import Decimal
from hashlib import sha256
import re

from .extraction import LLM_FIELDS, ListingFields, PreparedListing


KOREAN_DIGITS = "일이삼사오육칠팔구"
DIGIT = f"[{KOREAN_DIGITS}]"
KOREAN_NUMBER = (
    f"(?<![{KOREAN_DIGITS}십백천만])(?=[{KOREAN_DIGITS}십백천])"
    f"(?:{DIGIT}?천)?(?:{DIGIT}?백)?(?:{DIGIT}?십)?{DIGIT}?"
)
MONEY = rf"(?:\d[\d,]*(?:\.\d+)?\s*만\s*원?|\d[\d,]*\s*원|{KOREAN_NUMBER}만\s*원?)"
MONEY_RE = re.compile(MONEY)
SEATS = re.compile(r"\b([A-Z])-([0-9]{1,3})-([0-9]{1,3})\b|([A-Z])구역\s*(\d+)열\s*(\d+)번")


def money(value: str) -> int:
    clean = re.sub(r"[\s,원]", "", value)
    if "만" in clean:
        amount = clean.removesuffix("만")
        if amount[0].isdecimal():
            return round(Decimal(amount) * 10_000)
        units = {"십": 10, "백": 100, "천": 1000}
        total = digit = 0
        for char in amount:
            if char in units:
                total += (digit or 1) * units[char]
                digit = 0
            else:
                digit = KOREAN_DIGITS.index(char) + 1
        return (total + digit) * 10_000
    return int(clean)


def unit_price(text: str, count: re.Match | None, quantity: int | None) -> tuple[int | None, list[str]]:
    if re.search(r"가격[은이]?.*(?:미정|정하지|나중|추후)", text):
        return None, []
    total = re.search(r"합계\s*(" + MONEY + r")", text)
    if total and count and quantity:
        each, remainder = divmod(money(total[1]), quantity)
        if remainder == 0:
            return each, [total[0], count[0]]

    extra = re.search(r"(?:추가금|수고비)\s*(?:장당\s*)?(" + MONEY + r")", text)
    extra = extra or re.search(r"(" + MONEY + r")\s*추가", text)
    fee = re.search(r"예매\s*수수료\s*(" + MONEY + r")", text)
    charges = [match for match in (extra, fee) if match]
    excluded = {match.span(1) for match in charges}
    if total:
        excluded.add(total.span(1))
    explicit = [match for match in re.finditer(r"(?:장당|양도가)\s*(" + MONEY + r")", text)
                if match.span(1) not in excluded]
    if explicit:
        base = explicit[-1]
        value = money(base[1])
    else:
        base = next((m for m in MONEY_RE.finditer(text) if m.span() not in excluded), None)
        if base is None:
            return None, []
        value = money(base[0])
    evidence = [base[0]]
    if fee and "더해" in text:
        value += money(fee[1])
        evidence.append(fee[0])
    if extra and "포함" not in text:
        value += money(extra[1])
        evidence.append(extra[0])
    return value, evidence


def extract_local(listing: PreparedListing) -> dict:
    text = listing.title + "\n" + listing.body
    events = [event for event in listing.events if event["name"] in text]
    event = events[0] if len(events) == 1 else None
    matches = list(SEATS.finditer(text))
    seats = sorted({f"{m[1] or m[4]}-{int(m[2] or m[5]):02}-{int(m[3] or m[6]):02}" for m in matches}) or None
    count = re.search(r"(\d+)\s*장", text)
    quantity = (int(count[1]) or None) if count else None
    price, price_quotes = unit_price(text, count, quantity)
    evidence = {"seats": [m[0] for m in matches], "quantity": [count[0]] if quantity else [], "price_per_ticket_krw": price_quotes}
    method = next((word for word in ("아옮", "직링", "직거래") if word in text), None)
    values = {"event_id": event["event_id"] if event else None,
              "session_id": event["session_id"] if event else None,
              "seats": seats, "quantity": quantity, "price_per_ticket_krw": price, "trade_method": method}
    fields = ListingFields.model_validate({
        **values, "confidence": {key: 0.9 if values[key] is not None else 0.0 for key in LLM_FIELDS},
        "evidence": evidence,
    })
    ready = price is not None and bool(seats) and event is not None and quantity is not None
    reason = None if ready else "missing_price_or_seats"
    if price is not None and seats and event is not None and quantity is None:
        reason = "missing_quantity"
    return {
        "fields": fields.model_dump(), "schema_valid": True,
        "status": "extracted" if ready else "review", "reason": reason,
        "provider": "local", "source": "local_rules", "model_requested": "local-rules-v1",
        "model_returned": None, "attempts": 0, "input_tokens": 0, "output_tokens": 0,
        "fingerprint": sha256(("local-rules-v1" + listing.model_input).encode()).hexdigest(),
        "slang": listing.slang,
    }
