"""
Bootstrap TNEENWH SDK once at Django startup.

Follows the official integration guide exactly:
  tneenwh.configure → tneenwh.login → tneenwh.set_session

The module is imported by apps.security.apps.SecurityConfig.ready() so
configuration happens before the first OTP request.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def bootstrap_tneenwh() -> None:
    """Initialize TNEENWH SDK with credentials from Django settings."""
    logger.info("[TNEENWH] Bootstrap started")

    import tneenwh

    # 1. Configure base URL and user-agent (required for Cloudflare compat)
    tneenwh.configure(
        base_url=settings.TNEENWH_BASE_URL,
        user_agent=settings.TNEENWH_HTTP_USER_AGENT or None,
    )
    logger.info(
        "[TNEENWH] Configured | base_url=%s user_agent=%s",
        settings.TNEENWH_BASE_URL,
        settings.TNEENWH_HTTP_USER_AGENT[:40] + "..." if settings.TNEENWH_HTTP_USER_AGENT else "default",
    )

    # 2. Panel login — stores JWT token inside the library
    tneenwh.login(
        email=settings.TNEENWH_EMAIL,
        password=settings.TNEENWH_PASSWORD,
    )
    logger.info("[TNEENWH] Login successful | email=%s", settings.TNEENWH_EMAIL)

    # 3. Optional API key (Sub-API fallback)
    api_key = getattr(settings, "TNEENWH_API_KEY", "")
    if api_key:
        tneenwh.set_api_key(api_key)
        logger.info("[TNEENWH] API key set")

    # 4. Bind default WhatsApp session
    tneenwh.set_session(
        settings.TNEENWH_SESSION_ID,
        settings.TNEENWH_CHANNEL_SECRET,
    )
    logger.info(
        "[TNEENWH] Session attached | session_id=%s",
        settings.TNEENWH_SESSION_ID,
    )

    logger.info("[TNEENWH] Bootstrap completed successfully")


# Executed when the module is imported (during AppConfig.ready()).
bootstrap_tneenwh()
