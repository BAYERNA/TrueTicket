import os
from html import escape

import streamlit as st
from src.analyzer import analyze
from src.extractor import extract_from_sample, extract_with_llm
from src.privacy import require_demo_safe
from src.reporting import NOTICE, REPORTING_URL, SECTIONS, as_text
from src.repository import database, samples
from src.review_request import review_panel

STATES = {
    "CAUTION": "주의할 정황이 있습니다.",
    "REVIEW": "양도 조건을 추가로 확인하세요.",
    "INSUFFICIENT": "기준 자료가 부족해 판단을 보류합니다.",
}
STYLES = """<style>
.tg-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:12px 0}
.tg-card{padding:14px 16px;border:1px solid #bdccd2;border-left:4px solid #365f72;border-radius:8px}
.tg-card h3{font-size:1.02rem;margin:0 0 8px;padding:0}
.tg-card ul{padding-left:1.1rem;margin:0;line-height:1.65;font-size:.96rem}
.tg-card.signals{border-left-color:#a5681d}.tg-card.actions{border-left-color:#207e6e}
@media(max-width:767px){.tg-grid{grid-template-columns:minmax(0,1fr)}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stLinkButton"] a{width:100%;min-height:44px}}
</style>"""


def clear_result():
    st.session_state.pop("report", None)
    st.session_state.pop("feedback", None)


def set_sample():
    clear_result()
    choice = st.session_state.get("sample_choice")
    st.session_state["post_text"] = st.session_state.get("sample_texts", {}).get(choice, "")
    st.session_state["confirmed"] = False


def reset_category():
    clear_result()
    for key in ("sample_choice", "post_text", "confirmed"):
        st.session_state.pop(key, None)


def config(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        return None


def show_report(report):
    st.subheader("거래 전 점검 결과")
    st.write(f"{report['level']} · {STATES[report['level']]}")
    st.caption(f"추출 방식  {report['extraction_mode']} · {NOTICE}")
    cards = []
    for field, heading in SECTIONS:
        items = "".join(
            f"<li>{escape(item)}</li>" for item in report[field] or ["표시할 항목이 없습니다."]
        )
        cards.append(f'<section class="tg-card {field}"><h3>{heading}</h3><ul>{items}</ul></section>')
    st.markdown('<div class="tg-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.caption(f"가격 근거  {report['benchmark_source'] or '확인 불가'}")
    st.caption(f"정책 근거  {report['policy_source'] or '확인 불가'}")
    st.download_button(
        "TXT 진단 결과 다운로드",
        as_text(report).encode("utf-8"),
        file_name="TicketGuard_AI_진단결과.txt",
        mime="text/plain;charset=utf-8",
    )
    st.link_button("공식 신고센터 열기", REPORTING_URL)


def main():
    st.set_page_config(
        page_title="TicketGuard AI", layout="centered", initial_sidebar_state="collapsed"
    )
    st.markdown(STYLES, unsafe_allow_html=True)
    st.title("TicketGuard AI")
    st.write("송금 전에 양도 글을 읽고 가격과 입장 조건을 확인하세요.")
    st.caption(NOTICE)
    category = st.radio(
        "행사 종류", ("공연", "스포츠"), horizontal=True, key="category", on_change=reset_category
    )
    category_code = "PERFORMANCE" if category == "공연" else "SPORTS"
    with database() as conn:
        entries = {row["label"]: row for row in samples(conn, category_code)}
        st.session_state["sample_texts"] = {label: row["text"] for label, row in entries.items()}
        selected = st.selectbox(
            "시연 사례", [*entries, "직접 입력"], key="sample_choice", on_change=set_sample
        )
        st.session_state.setdefault("post_text", st.session_state["sample_texts"].get(selected, ""))
        text = st.text_area("판매 게시글", key="post_text", on_change=clear_result, max_chars=2400)
        consent = st.checkbox(
            "가상 게시글이며 실제 개인정보가 없음을 확인했습니다.",
            key="confirmed",
            on_change=clear_result,
        )
        use_ai = st.checkbox(
            "실제 LLM 추출 사용",
            on_change=clear_result,
            help="선택하면 분석할 가상 문장을 외부 모델에 보냅니다. 프리셋 모드는 외부 모델 호출 없이 동작합니다.",
        )
        if st.button("분석 시작", type="primary"):
            clear_result()
            try:
                require_demo_safe(text)
                if not consent:
                    raise ValueError("가상 게시글 확인란을 선택해 주세요.")
                if use_ai:
                    extracted = extract_with_llm(text, config("OPENAI_API_KEY"), config("OPENAI_MODEL"))
                else:
                    extracted = extract_from_sample(entries.get(selected), text)
                if extracted.get("category") and extracted["category"] != category_code:
                    raise ValueError("선택한 행사 종류와 추출된 행사 종류가 다릅니다.")
                st.session_state["report"] = analyze(extracted, conn, text)
            except ValueError as exc:
                st.session_state["feedback"] = str(exc)
    if "feedback" in st.session_state:
        st.error(st.session_state["feedback"])
    if "report" in st.session_state:
        show_report(st.session_state["report"])
    review_panel()


if __name__ == "__main__":
    main()
