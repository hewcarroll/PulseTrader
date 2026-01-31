"""Bot control endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ui.models import CashReleaseRequest

router = APIRouter()


@router.post("/start")
async def start_bot():
    return {"status": "ok", "message": "Bot start requested"}


@router.post("/stop")
async def stop_bot():
    return {"status": "ok", "message": "Bot stop requested"}


@router.post("/cash-release")
async def cash_release(request: CashReleaseRequest):
    return {"status": "ok", "amount": request.amount}
