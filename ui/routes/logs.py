"""Log viewing endpoints."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_logs():
    return {"status": "ok", "logs": []}
