"""Pydantic models for API payloads."""
from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str


class CashReleaseRequest(BaseModel):
    amount: float
