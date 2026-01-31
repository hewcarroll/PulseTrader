"""
PulseTrader.01 Admin UI
FastAPI application with TOTP + JWT authentication.
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from ui.auth import AuthManager
from ui.models import LoginRequest
from ui.routes import config, controls, dashboard, logs

app = FastAPI(
    title="PulseTrader.01 Admin",
    description="Autonomous Trading System Administration",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

BIND_ADDRESS = os.getenv("BIND_ADDRESS", "127.0.0.1")
BIND_PORT = int(os.getenv("BIND_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

auth_manager = AuthManager()
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user = await auth_manager.validate_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user


app.include_router(dashboard.router, prefix="/api/dashboard", dependencies=[Depends(get_current_user)])
app.include_router(controls.router, prefix="/api/controls", dependencies=[Depends(get_current_user)])
app.include_router(config.router, prefix="/api/config", dependencies=[Depends(get_current_user)])
app.include_router(logs.router, prefix="/api/logs", dependencies=[Depends(get_current_user)])


@app.post("/api/auth/login")
async def login(credentials: LoginRequest):
    result = await auth_manager.authenticate(
        credentials.username,
        credentials.password,
        credentials.totp_code,
    )

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])

    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "expires_in": result["expires_in"],
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pulsetrader"}


@app.exception_handler(Exception)
async def handle_exception(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting PulseTrader.01 Admin UI on {BIND_ADDRESS}:{BIND_PORT}")
    logger.warning("SECURITY: Only accessible via localhost. Use Tailscale for remote access.")

    uvicorn.run(app, host=BIND_ADDRESS, port=BIND_PORT, log_level="info")
