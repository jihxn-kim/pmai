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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
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
