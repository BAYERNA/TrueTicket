from datetime import datetime, timezone

SECTIONS = (
    ("facts", "확인된 사실"),
    ("signals", "의심 정황"),
    ("unknowns", "확인 불가"),
    ("actions", "권고 행동"),
)
REPORTING_URL = "https://www.culture.go.kr/singo/"
NOTICE = "가상 시연 데이터입니다. 법 위반 여부는 판단하지 않습니다."


def as_text(report):
    lines = [
        "TicketGuard AI | 거래 전 점검",
        NOTICE,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        f"검토 상태 {report['level']} · 추출 방식 {report['extraction_mode']}",
        "",
    ]
    for key, title in SECTIONS:
        lines.append(f"[{title}]")
        lines.extend(f"- {item}" for item in (report[key] or ["표시할 항목이 없습니다."]))
        lines.append("")
    lines.extend(
        [
            f"가격 근거  {report['benchmark_source'] or '확인 불가'}",
            f"정책 근거  {report['policy_source'] or '확인 불가'}",
            f"공식 신고센터  {REPORTING_URL}",
        ]
    )
    return "\n".join(lines)
