"""Dashboard endpoints."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_dashboard():
    return {"status": "ok", "message": "Dashboard data placeholder"}
