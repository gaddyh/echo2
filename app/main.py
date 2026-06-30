import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from app.config import Settings
from app.transcription import handle_360dialog_audio_message
from app.whatsapp import (
    Dialog360Client,
    expected_basic_auth_header,
    iter_incoming_messages,
)

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
        expected = expected_basic_auth_header(
            settings.webhook_basic_user,
            settings.webhook_basic_pass,
        )
        if (
            not settings.webhook_basic_user
            or not settings.webhook_basic_pass
            or authorization != expected
        ):
            raise HTTPException(status_code=401, detail="Unauthorized")
        return


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "360dialog-echo-bot"}


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

    Text message:
        echo: <text>

    Audio/voice message:
        downloads media -> converts if needed -> transcribes -> echo: <transcript>
    """
    verify_webhook_auth(authorization)

    payload = await request.json()
    logger.info("Incoming webhook payload: %s", payload)

    sent = []

    for message in iter_incoming_messages(payload):
        sender = message["from"]
        message_id = message["id"]
        msg_type = message["type"]

        try:
            if msg_type == "text":
                text = message.get("text", "")
                reply = f"echo: {text}"

            elif msg_type == "audio":
                media_id = message.get("media_id", "")
                mime_type = message.get("mime_type", "")

                if not media_id:
                    raise ValueError("Missing audio media id")

                await wa.send_text(
                    to=sender,
                    body="Transcribing your voice message...",
                )

                transcript = await handle_360dialog_audio_message(
                    wa=wa,
                    settings=settings,
                    media_id=media_id,
                    mime_type=mime_type,
                )

                reply = f"echo: {transcript}"

            else:
                continue

            logger.info(
                "Replying message_id=%s from=%s type=%s",
                message_id,
                sender,
                msg_type,
            )

            result = await wa.send_text(to=sender, body=reply)

            sent.append(
                {
                    "to": sender,
                    "message_id": message_id,
                    "type": msg_type,
                    "result": result,
                }
            )

        except Exception as exc:
            logger.exception(
                "Failed handling message_id=%s type=%s",
                message_id,
                msg_type,
            )

            await wa.send_text(
                to=sender,
                body="Sorry, I couldn't process that message.",
            )

            sent.append(
                {
                    "to": sender,
                    "message_id": message_id,
                    "type": msg_type,
                    "error": str(exc),
                }
            )

    return {
        "ok": True,
        "handled": len(sent),
        "sent": sent,
    }