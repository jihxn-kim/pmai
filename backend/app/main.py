from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

from app.config import settings

app = FastAPI(title="PM Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def structured_error_handler(request: Request, exc: Exception):
    from fastapi.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.status_code, "message": exc.detail}},
        )
    return JSONResponse(status_code=500, content={"error": {"code": 500, "message": "Internal server error"}})


@app.get("/api/health")
async def health():
    return {"status": "ok"}
