import base64
import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """360dialog expects international format digits, usually without '+'."""
    return (
        phone.replace("@c.us", "")
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .strip()
    )


class Dialog360Client:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.messages_url = f"{settings.d360_api_base_url}/messages"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "D360-API-KEY": self.settings.d360_api_key,
            "Content-Type": "application/json",
        }

    async def send_text(self, to: str, body: str) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalize_phone(to),
            "type": "text",
            "text": {"body": body},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(self.messages_url, headers=self.headers, json=payload)

        try:
            response_body: Any = response.json()
        except Exception:
            response_body = response.text

        if response.status_code not in {200, 201}:
            logger.error("360dialog send failed: status=%s body=%s", response.status_code, response_body)
            response.raise_for_status()

        return response_body


def iter_incoming_text_messages(payload: dict[str, Any]):
    """
    Yield {from, id, text, name} for every inbound text message in a
    WhatsApp/360dialog webhook payload.

    Status callbacks and unsupported message types are ignored.
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            contacts_by_wa_id = {
                contact.get("wa_id"): contact
                for contact in value.get("contacts", [])
                if contact.get("wa_id")
            }

            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue

                sender = message.get("from", "")
                contact = contacts_by_wa_id.get(sender, {})
                name = contact.get("profile", {}).get("name", "")

                yield {
                    "from": sender,
                    "id": message.get("id", ""),
                    "text": message.get("text", {}).get("body", ""),
                    "name": name,
                }


def expected_basic_auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"
