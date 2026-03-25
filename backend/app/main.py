from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.routers import auth, orgs, projects, tasks
from app.routers import github
from app.routers import dashboard
from app.routers import ai, briefings
from app.routers import slack
from app.routers import calendar
from app.routers import notion

try:
    from app.scheduler import scheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False

try:
    from app.services.ai.worker import recover_stuck_jobs
    HAS_WORKER = True
except ImportError:
    HAS_WORKER = False

from app.models.ai_job_queue import AIJobQueue, JobStatus
from app.database import async_session


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup
    if HAS_SCHEDULER:
        scheduler.start()
    if HAS_WORKER:
        await recover_stuck_jobs()
    yield
    # Shutdown: mark running AI jobs as queued for recovery on next start
    async with async_session() as db:
        running = await db.execute(
            select(AIJobQueue).where(AIJobQueue.status == JobStatus.running)
        )
        for job in running.scalars():
            job.status = JobStatus.queued
        await db.commit()
    if HAS_SCHEDULER:
        scheduler.shutdown()


app = FastAPI(title="PM Agent API", lifespan=lifespan)


# Fix HTTPS redirect behind Railway proxy
@app.middleware("http")
async def force_https_redirects(request: Request, call_next):
    response = await call_next(request)
    # If FastAPI generates a redirect, ensure it uses https when behind proxy
    if response.status_code in (301, 302, 307, 308):
        location = response.headers.get("location", "")
        if location.startswith("http://") and request.headers.get("x-forwarded-proto") == "https":
            response.headers["location"] = location.replace("http://", "https://", 1)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://frontend(-.*)?(-jihxns-projects)?\.vercel\.app|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": 422, "message": "Validation error", "detail": exc.errors()}},
    )


@app.exception_handler(Exception)
async def structured_error_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.status_code, "message": exc.detail}},
        )
    return JSONResponse(status_code=500, content={"error": {"code": 500, "message": "Internal server error"}})


@app.get("/api/debug/sdk")
async def debug_sdk():
    """Debug endpoint to check SDK and auth status."""
    import sys
    import subprocess
    info = {"python": sys.version}
    try:
        import claude_agent_sdk
        info["sdk"] = "installed"
        info["sdk_version"] = getattr(claude_agent_sdk, "__version__", "unknown")
    except ImportError as e:
        info["sdk"] = f"not installed: {e}"
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
        info["cli"] = result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        info["cli"] = f"error: {e}"
    try:
        result = subprocess.run(["claude", "auth", "status"], capture_output=True, text=True, timeout=10)
        info["auth"] = result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        info["auth"] = f"error: {e}"
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        info["node"] = result.stdout.strip()
    except Exception as e:
        info["node"] = f"error: {e}"
    import os
    info["has_anthropic_key"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
    info["has_claude_key"] = bool(os.environ.get("CLAUDE_API_KEY"))

    # Direct CLI test
    try:
        result = subprocess.run(
            ["claude", "-p", "say hello", "--output-format", "json", "--max-turns", "1"],
            capture_output=True, text=True, timeout=30
        )
        info["cli_test_stdout"] = result.stdout[:500] if result.stdout else ""
        info["cli_test_stderr"] = result.stderr[:500] if result.stderr else ""
        info["cli_test_exit"] = result.returncode
    except Exception as e:
        info["cli_test"] = f"error: {e}"

    return info

app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(github.router)
app.include_router(dashboard.router)
app.include_router(ai.router)
app.include_router(briefings.router)
app.include_router(slack.router)
app.include_router(calendar.router)
app.include_router(notion.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
