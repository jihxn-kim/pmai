from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import auth, orgs, projects, tasks
from app.routers import github
from app.routers import dashboard
from app.routers import ai, briefings

app = FastAPI(title="PM Agent API")

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


@app.get("/api/health")
async def health():
    return {"status": "ok"}
