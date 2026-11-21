"""동의받은 가상 한빛 사례의 선택 근거만 통합 접수함에 보낸다."""
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import streamlit as st

PORTAL = "https://ticketguard-ai-demo.tart-hippo-0446.chatgpt.site"
DEMO = json.loads((Path(__file__).resolve().parents[1] / "integration" / "hanbit_example.json").read_text(encoding="utf-8"))
FIELDS = DEMO["when_user_confirms"]


def send(workspace, key, indices):
    path = f"{PORTAL}/api/workspaces/{UUID(workspace)}/receipts"
    body = {"consent": True, "source": FIELDS["origin_post_id"], "evidence": indices, "key": key}
    request = Request(path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=12) as result:
            return json.load(result)["receipt"]
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        raise ValueError("접수 결과를 확인할 수 없습니다. 같은 근거로 재시도하거나 관객 초대 링크를 확인하세요.") from exc


def review_panel():
    with st.expander("한빛 콘서트 · 운영자에게 검토 요청"):
        st.write("2026 한빛 겨울 콘서트 1회차 · R석 두 장. 장당 제시액 137,000원, 가상 정가 110,000원.")
        workspace = st.query_params.get("w", "")
        try:
            workspace = str(UUID(workspace))
        except (ValueError, TypeError):
            st.link_button("한빛 콘서트 통합 시연 열기", PORTAL + "/?case=hanbit")
            return
        st.link_button("같은 공간의 공개 관객 화면 열기", f"{PORTAL}/?w={workspace}")
        evidence = FIELDS["chosen_evidence"]
        chosen = st.multiselect("보낼 근거 문구", evidence, default=evidence, key=f"evidence-{workspace}")
        consent = st.checkbox("가상 한빛 운영팀에 행사·회차, 글 번호, 좌석 후보, 제시액과 선택한 근거를 보내는 데 동의합니다.", key=f"consent-{workspace}")
        if st.button("선택 근거로 검토 접수"):
            if not chosen or not consent:
                st.warning("전송할 근거와 동의를 확인하세요.")
                return
            indices = sorted(evidence.index(s) for s in chosen)
            slot = f"request-{workspace}-{indices}"
            key = st.session_state.setdefault(slot, str(uuid4()))
            try:
                receipt = send(workspace, key, indices)
            except ValueError as exc:
                st.error(str(exc))
                return
            st.success("운영자 접수번호  " + receipt)
