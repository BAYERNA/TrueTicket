import asyncio
from contextlib import asynccontextmanager, closing
import json
import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from langgraph.checkpoint.sqlite import SqliteSaver

from .api import agent, cases, market
from .agent.action_graph import build_action_graph
from .agent.extraction import EVALUATION_FILENAME
from .agent.gemini import MODEL as GEMINI_MODEL, EMBEDDING_MODEL as GEMINI_EMBEDDING, api_key
from .db import Database
from .models import ScanRequest


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"


def create_app(database_path: Path | None = None, *, feed_port: int | None = None) -> FastAPI:
    database_path = database_path or Path(os.environ.get("TRUETICKET_DB", ROOT / "data" / "demo.sqlite3"))
    feed_port = feed_port if feed_port is not None else int(os.environ.get("TRUETICKET_FEED_PORT", "8000"))
    if not 1 <= feed_port <= 65535:
        raise ValueError("TRUETICKET_FEED_PORT는 1~65535 범위여야 합니다.")
    database = Database(database_path, ROOT / "data" / "seed.json")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.initialize()
        with closing(sqlite3.connect(database.path, check_same_thread=False)) as checkpoint_connection:
            app.state.action_graph = build_action_graph(database, SqliteSaver(checkpoint_connection))
            yield
            for task in app.state.active_runs.values():
                task.cancel()
            await asyncio.gather(*app.state.active_runs.values(), return_exceptions=True)
            if app.state.evaluation_task:
                app.state.evaluation_task.cancel()
                await asyncio.gather(app.state.evaluation_task, return_exceptions=True)

    application = FastAPI(title="TrueTicket", lifespan=lifespan)
    application.state.db = database
    application.state.feed_port = feed_port
    application.state.demo_lock = asyncio.Lock()
    application.state.active_runs = {}
    application.state.evaluation_task = None
    application.include_router(market.router)
    application.include_router(agent.router)
    application.include_router(cases.router)
    application.mount("/assets", StaticFiles(directory=DIST / "assets", check_dir=False), name="assets")
    application.mount("/licenses", StaticFiles(directory=DIST / "licenses", check_dir=False), name="licenses")

    @application.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @application.get("/api/events")
    def events(request: Request) -> list[dict]:
        return request.app.state.db.list_events()

    @application.post("/api/demo/reset")
    async def reset_demo(request: Request) -> dict:
        tasks = list(request.app.state.active_runs.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        evaluation_task = request.app.state.evaluation_task
        if evaluation_task and not evaluation_task.done():
            evaluation_task.cancel()
            await asyncio.gather(evaluation_task, return_exceptions=True)
        async with request.app.state.demo_lock:
            counts = await run_in_threadpool(request.app.state.db.reset)
        return {"status": "ok", "counts": counts}

    @application.get("/api/config")
    def config() -> dict:
        return {"gemini_configured": bool(api_key()), "extraction_model": GEMINI_MODEL,
                "embedding_model": GEMINI_EMBEDDING, "default_mode": "local",
                "local_mode_label": "규칙 데모", "synthetic_data_only": True}

    @application.get("/api/overview")
    def overview() -> dict:
        return database.overview()

    @application.get("/api/eval")
    def evaluation() -> dict:
        if application.state.evaluation_task and not application.state.evaluation_task.done():
            return {"status": "running"}
        full = ROOT / "data" / "evaluation" / "latest_results.json"
        if full.is_file():
            return json.loads(full.read_text(encoding="utf-8"))["summary"]
        path = ROOT / "data" / "evaluation" / EVALUATION_FILENAME
        if not path.is_file():
            return {
                "status": "not_run",
                "extraction_model": GEMINI_MODEL,
                "embedding_model": GEMINI_EMBEDDING,
            }
        return json.loads(path.read_text(encoding="utf-8"))["summary"]

    async def run_evaluation(mode: str):
        from .agent.gemini import AIUnavailable
        from .evaluation.full import evaluate
        from .evaluation.t4 import write_result

        async with application.state.demo_lock:
            try:
                report = await evaluate(mode, database)
            except AIUnavailable as error:
                report = {"summary": {"status": "api_error", "error": str(error), "validation_scope": mode,
                                       "ai_acceptance_verified": False}}
            except Exception:
                report = {"summary": {"status": "failed", "error": "evaluation_failed", "ai_acceptance_verified": False}}
            else:
                write_result(ROOT / "data/evaluation" / f"{mode}_results.json", report)
            write_result(ROOT / "data/evaluation/latest_results.json", report)

    @application.post("/api/eval", status_code=202)
    async def start_evaluation(filters: ScanRequest) -> dict:
        if application.state.active_runs or (application.state.evaluation_task and not application.state.evaluation_task.done()):
            raise HTTPException(409, "감시 또는 평가를 이미 실행하고 있습니다.")
        mode = filters.mode or "local"
        if mode == "gemini" and not api_key():
            raise HTTPException(409, "Gemini API 키를 서버 환경변수에 설정해 주세요.")
        application.state.evaluation_task = asyncio.create_task(run_evaluation(mode))
        return {"status": "running", "mode": mode}

    @application.get("/", include_in_schema=False)
    @application.get("/cases", include_in_schema=False)
    @application.get("/cases/{case_id}", include_in_schema=False)
    @application.get("/market", include_in_schema=False)
    def application_page() -> FileResponse:
        index = DIST / "index.html"
        if not index.is_file():
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "프론트엔드 빌드 후 /market을 열어 주세요.")
        return FileResponse(index)

    return application


app = create_app()
