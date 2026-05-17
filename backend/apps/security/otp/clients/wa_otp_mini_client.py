"""
HTTP client for the local wa-otp-mini WhatsApp service (Baileys-based).

The wa-otp-mini service runs as a separate Node.js process (e.g. via pm2)
and exposes a simple REST API on port 3001 (configurable via WA_OTP_MINI_URL).

Endpoints used:
  POST /send  — { phone: str, message: str }  → { ok: bool, ... }
  GET  /status — { ok: bool, connected: bool } → health check
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WaOtpMiniError(Exception):
    """Raised when the wa-otp-mini service returns an error or is unreachable."""


class WaOtpMiniClient:
    """Thin HTTP wrapper around the wa-otp-mini REST service."""

    def __init__(self):
        self._base_url = getattr(settings, "WA_OTP_MINI_URL", "http://127.0.0.1:3001").rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(self, *, phone: str, message: str) -> dict:
        """
        POST /send  →  { phone, message }

        Strips any non-digit characters from the phone number so the caller
        can pass E.164 format (+2526XXXXXXX) without adjustment.

        Raises WaOtpMiniError if the service is unreachable or returns ok=false.
        """
        clean_phone = "".join(c for c in phone if c.isdigit())
        try:
            resp = requests.post(
                f"{self._base_url}/send",
                json={"phone": clean_phone, "message": message},
                timeout=10,
            )
            resp.raise_for_status()
            data: dict = resp.json()
        except requests.RequestException as exc:
            raise WaOtpMiniError(f"wa-otp-mini unreachable: {exc}") from exc

        if not data.get("ok"):
            raise WaOtpMiniError(data.get("error", "wa-otp-mini returned ok=false"))

        return data

    def is_connected(self) -> bool:
        """GET /status — returns True if WhatsApp is connected."""
        try:
            resp = requests.get(f"{self._base_url}/status", timeout=5)
            return resp.json().get("connected", False)
        except requests.RequestException:
            return False
