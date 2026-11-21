"""선택한 한빛 근거를 공개 브라우저의 같은 공연 접수 양식에 전달한다."""
import json
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID, uuid4

import streamlit as st

PORTAL = "https://ticketguard-ai-demo.tart-hippo-0446.chatgpt.site"
DEMO = json.loads((Path(__file__).resolve().parents[1] / "integration" / "hanbit_example.json").read_text(encoding="utf-8"))
FIELDS = DEMO["when_user_confirms"]


def review_panel():
    with st.expander("한빛 콘서트 · 운영자에게 검토 요청"):
        st.write("2026 한빛 겨울 콘서트 1회차 · R석 두 장. 장당 제시액 137,000원, 가상 정가 110,000원.")
        try:
            workspace = str(UUID(st.query_params.get("w", "")))
        except (ValueError, TypeError):
            st.link_button("한빛 콘서트 통합 시연 열기", PORTAL + "/?case=hanbit")
            return
        evidence = FIELDS["chosen_evidence"]
        chosen = st.multiselect("보낼 근거 문구", evidence, default=evidence, key=f"evidence-{workspace}")
        st.caption("가상 한빛 운영팀에 보낼 항목을 선택하세요. 다음 화면에서 전송에 동의하면 접수번호를 확인할 수 있습니다.")
        if not chosen:
            return
        indices = ",".join(str(i) for i, text in enumerate(evidence) if text in chosen)
        slot = f"request-{workspace}-{indices}"
        if slot not in st.session_state:
            st.session_state[slot] = str(uuid4())
        fragment = urlencode({"e": indices, "k": st.session_state[slot]})
        st.link_button("선택 근거 확인 및 접수", f"{PORTAL}/?w={workspace}#{fragment}")
