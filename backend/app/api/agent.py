import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status

from ..agent.monitor import build_monitor
from ..agent.gemini import api_key as gemini_api_key
from ..models import ScanRequest


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/runs")
async def start_scan(request: Request, filters: ScanRequest) -> dict:
    filters = filters.model_copy(update={"mode": filters.mode or "local"})
    if filters.mode == "gemini" and not gemini_api_key():
        raise HTTPException(409, "Gemini API 키를 서버 환경변수에 설정해 주세요. 규칙 데모도 사용할 수 있습니다.")
    if filters.event_id and filters.event_id not in {event["id"] for event in request.app.state.db.list_events()}:
        raise HTTPException(404, "공연을 찾을 수 없습니다.")
    evaluation_task = request.app.state.evaluation_task
    if request.app.state.active_runs or (evaluation_task and not evaluation_task.done()):
        raise HTTPException(409, "이미 감시를 실행하고 있습니다.")
    run_id = uuid4().hex
    request.app.state.active_runs[run_id] = asyncio.create_task(run_monitor(request, filters, run_id))
    return {"run_id": run_id, "status": "running", "mode": filters.mode}


async def run_monitor(request: Request, filters: ScanRequest, run_id: str) -> None:
    try:
        async with request.app.state.demo_lock:
            graph = build_monitor(request.app.state.db, request.app.state.feed_port)
            await graph.ainvoke({"run_id": run_id, "event_id": filters.event_id, "mode": filters.mode})
    except asyncio.CancelledError:
        raise
    except Exception:
        request.app.state.db.record_agent_step(run_id, filters.event_id, "failed", "monitor", {"error": "analysis_failed"}, 0)
    finally:
        request.app.state.active_runs.pop(run_id, None)


@router.get("/runs/{run_id}")
def get_scan(request: Request, run_id: str) -> dict:
    steps = request.app.state.db.read_run(run_id)
    running = run_id in request.app.state.active_runs
    if not steps and not running:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "감시 실행 기록을 찾을 수 없습니다.")
    state = "running"
    if not running:
        last = steps[-1]
        if last["step"] == "assess":
            state = last["output_summary"].get("status", "completed")
        elif steps[0]["step"] == "collect" and "mode" not in steps[0]["output_summary"] and last["step"] in {"collect", "extract"}:
            # Older runs ended after collection or extraction.
            state = "failed" if steps[0]["output_summary"].get("status") == "failed" else "completed"
        else:
            state = "failed"
    return {"run_id": run_id, "status": state, "steps": steps}
