from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from langgraph.types import Command
from starlette.concurrency import run_in_threadpool

from ..models import ActionRequest, ApprovalRequest, SimulationRequest
from ..services.actions import draft_document, prepare_approval, require_case, simulate


router = APIRouter(prefix="/api", tags=["cases"])


@router.get("/cases")
def cases(request: Request, event_id: str | None = Query(default=None, max_length=64),
          risk: str | None = Query(default=None, max_length=20)) -> list[dict]:
    return request.app.state.db.list_cases(event_id, risk)


@router.get("/cases/{case_id}")
def case_detail(request: Request, case_id: str) -> dict:
    return require_case(request.app.state.db, case_id)


def create_approval(request: Request, case_id: str, kind: str) -> dict:
    state = prepare_approval(request.app.state.db, case_id, kind)
    config = {"configurable": {"thread_id": state["approval_id"]}}
    request.app.state.action_graph.invoke(state, config)
    return {**state, "status": "awaiting_approval"}


@router.post("/cases/{case_id}/approvals")
async def approval_preview(request: Request, case_id: str, body: ApprovalRequest) -> dict:
    async with request.app.state.demo_lock:
        return await run_in_threadpool(create_approval, request, case_id, body.type)


def apply_action(request: Request, case_id: str, body: ActionRequest) -> dict:
    if not body.approved:
        raise HTTPException(403, "운영자 승인이 필요합니다.")
    graph = request.app.state.action_graph
    approval_id = body.approval_id
    if approval_id is None:
        approval_id = create_approval(request, case_id, body.type)["approval_id"]
    config = {"configurable": {"thread_id": approval_id}}
    state = graph.get_state(config)
    if not state.values or state.values.get("case_id") != case_id or state.values.get("type") != body.type:
        raise HTTPException(403, "승인 요청이 케이스 또는 조치와 일치하지 않습니다.")
    if state.values.get("result"):
        return {"action": state.values["result"], "case": require_case(request.app.state.db, case_id), "replayed": True}
    result = graph.invoke(Command(resume={"approved": True, "edited_text": body.edited_text}), config)
    return {"action": result["result"], "case": require_case(request.app.state.db, case_id), "replayed": False}


@router.post("/cases/{case_id}/actions")
async def action(request: Request, case_id: str, body: ActionRequest) -> dict:
    if body.approved is not True:
        raise HTTPException(403, "운영자 승인이 필요합니다.")
    async with request.app.state.demo_lock:
        return await run_in_threadpool(apply_action, request, case_id, body)


@router.post("/cases/{case_id}/simulate")
async def simulate_case(request: Request, case_id: str, body: SimulationRequest) -> dict:
    async with request.app.state.demo_lock:
        return await run_in_threadpool(simulate, request.app.state.db, case_id, body.type, body.text)


@router.get("/cases/{case_id}/report")
def report(request: Request, case_id: str) -> Response:
    case = require_case(request.app.state.db, case_id)
    document = draft_document(case, "draft_report")
    return Response(document["text"], media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="TrueTicket-{case_id}-report.txt"'})
