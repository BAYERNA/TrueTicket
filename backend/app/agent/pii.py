from dataclasses import dataclass
import re


EMAIL = re.compile(r"(?<![\w.+-])[A-Z\d._%+-]+@[A-Z\d.-]+\.[A-Z]{2,}(?![A-Z\d-])", re.I)
ACCOUNT = re.compile(
    r"((?:입금[ \t]*계좌|계좌(?:[ \t]*번호)?)[ \t]*(?:[:：=][ \t]*|[ \t]+)"
    r"(?:[가-힣A-Za-z]+[ \t]+){0,2})"
    r"(\d(?:[ -]?\d){8,15})(?![\d-])"
)
PHONE = re.compile(
    r"(?<![\dA-Za-z])(?:(?:\+82[ .-]?(?:\(0\))?[ .-]?0?1[016789])|"
    r"(?:01[016789]|02|0[3-6]\d|070))[ .-]?\d{3,4}[ .-]?\d{4}(?!\d)"
)
NAME = re.compile(
    r"((?:예금주|실명|이름|성함|예매자명|예약자명)[ \t]*(?:[:：=][ \t]*|[ \t]+))"
    r"([가-힣]{2,6}|[A-Za-z][A-Za-z'-]*(?:[ \t]+[A-Za-z][A-Za-z'-]*){0,3})"
    r"(?=[ \t]*(?:[/|,;.\n]|$))"
)


@dataclass(frozen=True)
class MaskedText:
    text: str
    counts: dict[str, int]


def mask_pii(text: str) -> MaskedText:
    text, bank = ACCOUNT.subn(r"\g<1>[계좌 마스킹]", text)
    text, phones = PHONE.subn("[전화 마스킹]", text)
    text, emails = EMAIL.subn("[이메일 마스킹]", text)
    text, names = NAME.subn(r"\g<1>[이름 마스킹]", text)
    return MaskedText(text, {
        "bank_account": bank,
        "phone": phones,
        "email": emails,
        "name": names,
    })
