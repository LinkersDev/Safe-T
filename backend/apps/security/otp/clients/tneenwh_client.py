"""
TNEENWH WhatsApp API synchronous client.

Uses the official ``tneenwh`` Python package (PyPI) so we don't have to
reverse-engineer endpoints, headers, or payload shapes.

If ``tneenwh`` is not installed a clear error is raised with install
instructions.
"""
from __future__ import annotations

import logging
import socket
from urllib.error import URLError

from django.conf import settings

logger = logging.getLogger(__name__)


class TneenwhError(Exception):
    """Base exception for TNEENWH client errors."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class TneenwhAuthError(TneenwhError):
    """Raised when API key / channel secret is rejected."""


class TneenwhTimeoutError(TneenwhError):
    """Raised when the request exceeds the configured timeout."""


class TneenwhAPIError(TneenwhError):
    """Raised for non-2xx responses that are not auth-related."""


class TneenwhClient:
    """
    Thin wrapper around the pre-bootstrapped TNEENWH SDK.

    The SDK is configured, authenticated, and session-bound once at
    Django startup (see tneenwh_bootstrap.py).  This class only:

    * Formats phone numbers to ``{digits}@c.us``.
    * Calls ``tneenwh.send_text()`` (already authenticated).
    * Wraps errors into our own exception hierarchy.
    * Adds detailed request/response logging.
    """

    DEFAULT_TIMEOUT = 15  # seconds

    def __init__(
        self,
        session_id: str | None = None,
        channel_secret: str | None = None,
        timeout: int | None = None,
    ):
        self.session_id = session_id or getattr(settings, "TNEENWH_SESSION_ID", "")
        self.channel_secret = channel_secret or getattr(settings, "TNEENWH_CHANNEL_SECRET", "")
        self.timeout = timeout or self.DEFAULT_TIMEOUT

    @staticmethod
    def _format_recipient(phone: str) -> str:
        """
        Convert a phone number to TNEENWH's expected ``{digits}@c.us`` format.

        * Strips leading '+' if present.
        * Appends '@c.us' if missing.
        """
        cleaned = phone.lstrip("+")
        if "@" not in cleaned:
            cleaned = f"{cleaned}@c.us"
        return cleaned

    def send_message(self, *, to: str, message: str) -> dict:
        """
        Send a plain-text WhatsApp message via the pre-bootstrapped TNEENWH SDK.

        The SDK is already authenticated and session-bound at Django startup,
        so this method only needs to format the recipient and call ``send_text``.

        Args:
            to: Phone number in any common format (e.g. +201234567890).
            message: Text body to deliver.

        Returns:
            Parsed JSON response from TNEENWH.

        Raises:
            TneenwhAuthError: on 401/403 responses.
            TneenwhTimeoutError: on socket/read timeout.
            TneenwhAPIError: on other non-2xx responses.
            TneenwhError: on network or configuration issues.
        """
        try:
            import tneenwh
            from tneenwh import TneenwhApiError, FeatureNotSupportedError
        except ModuleNotFoundError as exc:
            raise TneenwhError(
                "The 'tneenwh' package is required for WhatsApp OTP delivery. "
                "Install it with: pip install tneenwh"
            ) from exc

        if not self.session_id:
            raise TneenwhError("TNEENWH_SESSION_ID is not configured.")
        if not self.channel_secret:
            raise TneenwhError("TNEENWH_CHANNEL_SECRET is not configured.")

        recipient = self._format_recipient(to)

        logger.info("[TNEENWH SEND] Starting | destination=%s", recipient)
        logger.debug(
            "[TNEENWH SEND] Payload preview | to=%s message_preview=%s...",
            recipient,
            message[:50],
        )

        try:
            # SDK already configured, logged-in, and session-bound at startup.
            # tneenwh_bootstrap.py calls configure → login → set_session.
            result = tneenwh.send_text(recipient, message)

            logger.info(
                "[TNEENWH SEND] Success | destination=%s result=%s",
                recipient,
                result,
            )
            return result if isinstance(result, dict) else {"result": result}

        except TneenwhApiError as exc:
            status = getattr(exc, "status", None)
            body = getattr(exc, "body", None)
            logger.error(
                "[TNEENWH SEND] Failed | destination=%s status=%s body=%s",
                recipient,
                status,
                body,
                exc_info=True,
            )
            if getattr(exc, "is_unauthorized", lambda: False)():
                raise TneenwhAuthError(
                    "TNEENWH authentication failed. Check session / channel secret.",
                    status_code=status,
                    response_body=body,
                ) from exc
            raise TneenwhAPIError(
                f"TNEENWH API returned {status or 'unknown'}.",
                status_code=status,
                response_body=body,
            ) from exc
        except FeatureNotSupportedError as exc:
            logger.error(
                "[TNEENWH SEND] Feature not supported | destination=%s error=%s",
                recipient,
                exc,
                exc_info=True,
            )
            raise TneenwhError(f"TNEENWH feature not supported: {exc}") from exc
        except (socket.timeout, TimeoutError) as exc:
            logger.error(
                "[TNEENWH SEND] Timed out | destination=%s after %ss",
                recipient,
                self.timeout,
                exc_info=True,
            )
            raise TneenwhTimeoutError(
                f"TNEENWH request timed out after {self.timeout}s."
            ) from exc
        except URLError as exc:
            logger.error(
                "[TNEENWH SEND] Network error | destination=%s error=%s",
                recipient,
                exc,
                exc_info=True,
            )
            raise TneenwhError(f"TNEENWH request failed: {exc}") from exc
