"""Authentication manager for the admin UI."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict

import jwt
import pyotp
from loguru import logger


class AuthManager:
    """Handle authentication and JWT issuance."""

    def __init__(self) -> None:
        self.secret_key = os.getenv("JWT_SECRET_KEY", "")
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")
        self.totp_secret = os.getenv("TOTP_SECRET", "")

    async def authenticate(self, username: str, password: str, totp_code: str) -> Dict:
        if username != self.admin_username or password != self.admin_password:
            return {"success": False, "message": "Invalid username or password"}

        if not self._verify_totp(totp_code):
            return {"success": False, "message": "Invalid TOTP code"}

        token = self._create_token({"sub": username})
        return {
            "success": True,
            "access_token": token,
            "expires_in": 3600,
        }

    async def validate_token(self, token: str) -> Dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return {"username": payload.get("sub")}
        except jwt.PyJWTError as exc:
            logger.warning(f"Token validation failed: {exc}")
            return {}

    def _create_token(self, data: Dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=1)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm="HS256")

    def _verify_totp(self, totp_code: str) -> bool:
        if not self.totp_secret:
            logger.warning("TOTP secret not configured")
            return False

        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(totp_code)
