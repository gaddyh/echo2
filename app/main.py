import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from app.config import Settings
from app.whatsapp import Dialog360Client, expected_basic_auth_header, iter_incoming_text_messages

settings = Settings.from_env()
logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="360dialog Echo Bot")
wa = Dialog360Client(settings)


def verify_webhook_auth(authorization: str | None) -> None:
    if settings.webhook_auth_mode == "none":
        return

    if settings.webhook_auth_mode == "bearer":
        expected = f"Bearer {settings.webhook_bearer_token}"
        if not settings.webhook_bearer_token or authorization != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return

    if settings.webhook_auth_mode == "basic":
        expected = expected_basic_auth_header(settings.webhook_basic_user, settings.webhook_basic_pass)
        if not settings.webhook_basic_user or not settings.webhook_basic_pass or authorization != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/360dialog")
async def webhook_360dialog(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    360dialog webhook endpoint.

    It parses inbound text messages and replies with:
        echo: <user text>

    Status callbacks are acknowledged and ignored.
    """
    verify_webhook_auth(authorization)

    payload = await request.json()
    logger.info("Incoming webhook payload: %s", payload)

    sent = []
    for message in iter_incoming_text_messages(payload):
        sender = message["from"]
        text = message["text"]
        reply = f"echo: {text}"

        logger.info("Echoing message_id=%s from=%s text=%r", message["id"], sender, text)
        result = await wa.send_text(to=sender, body=reply)
        sent.append({"to": sender, "message_id": message["id"], "result": result})

    return {"ok": True, "echoed": len(sent), "sent": sent}
