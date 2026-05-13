# TNEENWH + Django — integration guide

Use the official **`tneenwh`** package with Django. Production API: **`https://api.tneenwh.com`**.

- Every function and error: [`TNEENWH-LIBRARY-REFERENCE.md`](./TNEENWH-LIBRARY-REFERENCE.md)
- Concepts: [`TNEENWH-SDK.md`](./TNEENWH-SDK.md)
- HTTP: [`openapi.json`](../openapi.json)

Panel flows use **`tneenwh.configure`**, **`tneenwh.login`** (stores JWT inside the library), then **`tneenwh.set_session(session_id, channel_secret)`**. After that, call only **`tneenwh.*`** and **`Channel`** methods—no hand-written HTTP clients.

---

## Install

```bash
pip install tneenwh
# monorepo: pip install -e ./packages/tneenwh-python
```

---

## Wire Django once (`AppConfig.ready`)

```python
# whatsapp/apps.py
from django.apps import AppConfig


class WhatsappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "whatsapp"

    def ready(self):
        from . import tneenwh_bootstrap  # noqa: F401
```

```python
# whatsapp/tneenwh_bootstrap.py
from django.conf import settings

import tneenwh


def bootstrap_tneenwh() -> None:
    tneenwh.configure(
        base_url=settings.TNEENWH_BASE_URL,
        user_agent=settings.TNEENWH_HTTP_USER_AGENT or None,
    )
    tneenwh.login(email=settings.TNEENWH_EMAIL, password=settings.TNEENWH_PASSWORD)
    if getattr(settings, "TNEENWH_API_KEY", ""):
        tneenwh.set_api_key(settings.TNEENWH_API_KEY)
    tneenwh.set_session(settings.TNEENWH_SESSION_ID, settings.TNEENWH_CHANNEL_SECRET)


bootstrap_tneenwh()
```

```python
# settings.py (excerpt)
import os

TNEENWH_BASE_URL = os.environ.get("TNEENWH_BASE_URL", "https://api.tneenwh.com").rstrip("/")
TNEENWH_EMAIL = os.environ["TNEENWH_EMAIL"]
TNEENWH_PASSWORD = os.environ["TNEENWH_PASSWORD"]
TNEENWH_SESSION_ID = os.environ["TNEENWH_SESSION_ID"]
TNEENWH_CHANNEL_SECRET = os.environ["TNEENWH_CHANNEL_SECRET"]
TNEENWH_HTTP_USER_AGENT = os.environ.get(
    "TNEENWH_HTTP_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
)
TNEENWH_API_KEY = os.environ.get("TNEENWH_API_KEY", "").strip()  # optional; else fill via me() below
```

---

## Webhook endpoint (Django only parses the request; TNEENWH calls stay in the library)

Register with **`tneenwh.set_webhook(url, events)`** after bootstrap. On **`message`** events with **`payload.media.ticket`**, call **`tneenwh.download_inbound_media(ticket)`** (or pass **`session_id=`** / **`channel_secret=`** if you did not set a default session). Resolve **`channel_secret`** for an unknown **`sessionId`** with **`tneenwh.get_channel_secret(session_id)["channelSecret"]`**.

Use **`@csrf_exempt`** on the webhook URL. Return **200** quickly.

---

## One real-world example — every library entry point

Below is one management command: **`whatsapp/management/commands/tneenwh_library_demo.py`**. It runs **`bootstrap_tneenwh()`**, then calls **every** export on **`tneenwh`** plus **representative** **`Channel`** methods (same HTTP as the module; `Channel` also exposes **`group_*`** mirroring **`tneenwh.group_*`**).

**Note:** **`send_media`** and **`group_set_picture`** take a **`base64_data`** string as required by the API; the demo uses a tiny literal GIF in that form so there is no file I/O—only **`tneenwh`** performs HTTP.

Set **`TNEENWH_GROUP_JID`** (e.g. `120363...@g.us`) to exercise group helpers. Destructive calls stay **commented**.

```python
# whatsapp/management/commands/tneenwh_library_demo.py
"""
Every tneenwh library entry point from Django (no manual HTTP).
Run: python manage.py tneenwh_library_demo
"""
from __future__ import annotations

import os

from django.core.management.base import BaseCommand

import tneenwh
from tneenwh import (
    MCP_FOCUS_SESSION_HEADER,
    PANEL_MCP_SUBPATH,
    FeatureNotSupportedError,
    OtpNotificationParams,
    TneenwhApiError,
    format_otp_notification_message,
    is_api_error,
    is_feature_not_supported,
    mcp_focus_sessions_header,
    panel_mcp_url,
)

# Tiny GIF as base64 — API expects base64_data; no extra HTTP libraries involved.
_TINY_GIF_B64 = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"


def _run_group_demo(peer: str, group_jid: str, tiny_b64: str, log) -> None:
    ops = [
        ("group_get", lambda: tneenwh.group_get(group_jid)),
        ("group_participants_add", lambda: tneenwh.group_participants_add(group_jid, [peer])),
        ("group_participants_remove", lambda: tneenwh.group_participants_remove(group_jid, [peer])),
        ("group_admins_promote", lambda: tneenwh.group_admins_promote(group_jid, [peer])),
        ("group_admins_demote", lambda: tneenwh.group_admins_demote(group_jid, [peer])),
        ("group_set_subject", lambda: tneenwh.group_set_subject(group_jid, "Subject")),
        ("group_set_description", lambda: tneenwh.group_set_description(group_jid, "Description")),
        ("group_invite_code", lambda: tneenwh.group_invite_code(group_jid)),
        ("group_revoke_invite", lambda: tneenwh.group_revoke_invite(group_jid)),
        ("group_set_add_members_admins_only", lambda: tneenwh.group_set_add_members_admins_only(group_jid, True)),
        ("group_set_messages_admins_only", lambda: tneenwh.group_set_messages_admins_only(group_jid, False)),
        ("group_set_info_admins_only", lambda: tneenwh.group_set_info_admins_only(group_jid, False)),
        (
            "group_set_picture",
            lambda: tneenwh.group_set_picture(
                group_jid, mimetype="image/gif", base64_data=tiny_b64
            ),
        ),
        ("group_delete_picture", lambda: tneenwh.group_delete_picture(group_jid)),
        ("group_membership_requests", lambda: tneenwh.group_membership_requests(group_jid)),
        ("group_membership_approve", lambda: tneenwh.group_membership_approve(group_jid, None)),
        ("group_membership_reject", lambda: tneenwh.group_membership_reject(group_jid, None)),
    ]
    for name, fn in ops:
        try:
            log(f"{name}: {fn()}")
        except TneenwhApiError as e:
            log(f"{name}: TneenwhApiError {e.status} {e}")


class Command(BaseCommand):
    help = "Exercise the full tneenwh Python surface (safe defaults)."

    def handle(self, *args, **options):
        from whatsapp.tneenwh_bootstrap import bootstrap_tneenwh

        bootstrap_tneenwh()

        sid = os.environ["TNEENWH_SESSION_ID"]
        sec = os.environ["TNEENWH_CHANNEL_SECRET"]
        peer = os.environ.get("TNEENWH_PEER_JID", "201234567890@c.us")
        group_jid = os.environ.get("TNEENWH_GROUP_JID", "").strip()

        def log(msg: str) -> None:
            self.stdout.write(str(msg))

        log(tneenwh.health())

        cfg = tneenwh.get_config()
        log(f"get_config base_url={cfg.base_url}")
        # tneenwh.set_base_url("https://api.tneenwh.com")
        # tneenwh.set_bearer_token("…")  # only if not using login() in bootstrap

        me = tneenwh.me()
        log(me)
        if isinstance(me, dict) and me.get("apiKey") and not cfg.api_key:
            tneenwh.set_api_key(str(me["apiKey"]))
        log(tneenwh.profile())
        log(tneenwh.channel_secrets())
        # tneenwh.rotate_swagger_portal()

        # tneenwh.signup_send_otp(name="…", phone="+…", email="…", password="…")
        # tneenwh.signup_verify(email="…", code="123456")  # tneenwh.verify_otp alias

        log(tneenwh.sessions_list())
        # log(tneenwh.session_create("Demo"))
        log(tneenwh.get_channel_secret(sid))
        tneenwh.set_session(sid, sec)
        # tneenwh.set_apikey(me["apiKey"])  # alias of set_api_key

        # tneenwh.session_update(sid, sec, name="Renamed")
        # tneenwh.session_disconnect(sid, sec)
        # tneenwh.session_delete(sid, sec)

        log(tneenwh.session_status())
        log(tneenwh.session_details())
        log(tneenwh.session_qr())
        # tneenwh.refresh_session_qr()

        log(tneenwh.send_text(peer, "send_text"))
        log(tneenwh.send_message({"to": peer, "message": "send_message"}))
        log(
            tneenwh.send_media(
                peer,
                mimetype="image/gif",
                base64_data=_TINY_GIF_B64,
                filename="px.gif",
                caption="demo",
            )
        )
        log(
            tneenwh.send_list_message(
                peer,
                button_text="Pick",
                sections=[{"title": "A", "rows": [{"id": "1", "title": "One"}]}],
                title="Menu",
            )
        )

        otp_params: OtpNotificationParams = {
            "from_name": "Acme",
            "receiver_id": "req-1",
            "otp": "123456",
            "user_name": "Ada",
        }
        log(tneenwh.send_text(peer, format_otp_notification_message(**otp_params)))

        log(tneenwh.send_chat_state(peer, "typing"))
        log(tneenwh.send_chat_state(peer, "stop"))
        log(tneenwh.session_chat_state(peer, "recording"))
        log(tneenwh.session_chat_state(peer, "stop"))

        incoming = tneenwh.session_incoming()
        log(incoming)
        log(tneenwh.session_events())
        log(tneenwh.session_calls())

        ticket = None
        if isinstance(incoming, dict):
            for item in incoming.get("items") or []:
                if not isinstance(item, dict):
                    continue
                media = item.get("media")
                if isinstance(media, dict) and media.get("ticket"):
                    ticket = str(media["ticket"])
                    break

        wh_url = os.environ.get("TNEENWH_WEBHOOK_URL", "https://example.com/whatsapp/webhook/")
        log(
            tneenwh.set_webhook(
                wh_url,
                ["message", "call", "ready", "qr", "disconnected", "auth_failure"],
            )
        )

        log(tneenwh.v1_sessions_list())
        log(tneenwh.v1_send_message(sid, sec, {"to": peer, "message": "v1_send_message"}))
        log(tneenwh.v1_send_chat_state(sid, sec, to=peer, state="typing"))
        log(tneenwh.v1_send_chat_state(sid, sec, to=peer, state="stop"))

        ch = tneenwh.session(sid, sec)
        log(ch.status())
        log(ch.details())
        log(ch.qr())
        log(ch.get_channel_secret())
        log(ch.incoming())
        log(ch.events())
        log(ch.calls())
        log(ch.set_webhook(wh_url, ["message"]))
        if ticket:
            body, ctype = tneenwh.download_inbound_media(ticket)
            log(f"download_inbound_media {len(body)} bytes {ctype}")
            body2, ctype2 = ch.download_inbound_media(ticket)
            log(f"Channel.download_inbound_media {len(body2)} bytes {ctype2}")
        # ch.refresh_qr()
        log(ch.send_text(peer, "Channel.send_text"))
        log(ch.send_message({"to": peer, "message": "Channel.send_message"}))
        log(
            ch.send_media(
                peer,
                mimetype="image/gif",
                base64_data=_TINY_GIF_B64,
                filename="c.gif",
            )
        )
        log(
            ch.send_list_message(
                peer,
                button_text="Go",
                sections=[{"title": "B", "rows": [{"id": "2", "title": "Two"}]}],
            )
        )
        log(ch.send_chat_state(peer, "typing"))
        log(ch.send_chat_state(peer, "stop"))

        if group_jid:
            try:
                log(tneenwh.create_group("Lib demo", participants=[peer]))
            except TneenwhApiError as e:
                log(f"create_group: {e}")
            try:
                log(ch.group_get(group_jid))
            except TneenwhApiError as e:
                log(f"Channel.group_get: {e}")
            _run_group_demo(peer, group_jid, _TINY_GIF_B64, log)
            # tneenwh.group_leave(group_jid)

        # tneenwh.rotate_channel_secret(sid, sec)
        # ch.rotate_channel_secret()

        try:
            tneenwh.set_status()
        except FeatureNotSupportedError as e:
            log(f"set_status → {e}")

        log(panel_mcp_url(cfg.base_url))
        log(mcp_focus_sessions_header(sid))
        log(MCP_FOCUS_SESSION_HEADER)
        log(PANEL_MCP_SUBPATH)

        try:
            tneenwh.get_channel_secret("00000000-0000-0000-0000-000000000000")
        except TneenwhApiError as e:
            log(f"is_api_error={is_api_error(e)} status={e.status}")

        try:
            tneenwh.set_status()
        except FeatureNotSupportedError as e:
            log(f"is_feature_not_supported={is_feature_not_supported(e)}")

        # tneenwh.logout()
```

### Notes

- **`create_group`** and some **`group_*`** / **`group_membership_*`** calls may fail if the server build omits group routes—**`TneenwhApiError`** is expected in those cases.
- **Aliases** (same HTTP; not invoked twice here): **`generate_otp`**, **`request_signup_otp`**, **`verify_otp`**, **`set_apikey`**.
- Remaining **`Channel`** **`group_*`** methods match **`tneenwh.group_*`** signatures if you prefer **`ch.group_participants_add(...)`** over the module function.

---

## Reference

| Doc | Purpose |
|-----|---------|
| [`TNEENWH-LIBRARY-REFERENCE.md`](./TNEENWH-LIBRARY-REFERENCE.md) | Full method list and HTTP status behavior |
| [`USER_GUIDE_PYTHON_DJANGO.md`](./USER_GUIDE_PYTHON_DJANGO.md) | Webhook JSON shapes (human-readable tables) |
