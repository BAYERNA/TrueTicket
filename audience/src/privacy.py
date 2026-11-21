import re
import unicodedata

PATTERNS = {
    "전화번호": re.compile(r"(?<!\d)(?:\+82[ .-]?1[016789]|01[016789])[ .-]?\d{3,4}[ .-]?\d{4}(?!\d)"),
    "이메일": re.compile(r"[\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}"),
    "계좌번호 의심": re.compile(r"(?<!\d)(?:\d{2,6}[ -]\d{2,6}[ -]\d{3,8}|\d{10,16})(?!\d)"),
}


def detect_personal_data(text):
    normalized = unicodedata.normalize("NFKC", text)
    return [label for label, pattern in PATTERNS.items() if pattern.search(normalized)]


def require_demo_safe(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("가상 판매글을 입력하세요.")
    if len(text) > 2400:
        raise ValueError("가상 판매글은 2,400자까지 분석할 수 있습니다.")
    if detect_personal_data(text):
        raise ValueError("개인정보로 보이는 항목이 있습니다. 해당 정보를 지운 가상 글을 사용하세요.")
