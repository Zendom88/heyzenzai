"""
WhatsApp Cloud API client (Meta).
Handles sending messages and parsing incoming webhook payloads.
"""
import httpx
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_API_BASE = "https://graph.facebook.com/v19.0"


async def send_whatsapp_message(
    to: str,
    message: str,
    phone_number_id: Optional[str] = None,
) -> dict:
    """
    Send a plain text WhatsApp message via Cloud API.
    `to` must be in E.164 format (e.g. +6591234567).
    """
    phone_id = phone_number_id or settings.whatsapp_phone_number_id
    url = f"{WHATSAPP_API_BASE}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),  # Meta expects no leading +
        "type": "text",
        "text": {"body": message, "preview_url": False},
    }
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def send_interactive_buttons(
    to: str,
    body_text: str,
    buttons: list[dict],  # [{"id": "slot_1", "title": "Thu 3:00 PM"}, ...]
    phone_number_id: Optional[str] = None,
) -> dict:
    """
    Send interactive quick-reply buttons.
    Max 3 buttons per message (Meta limit).
    """
    phone_id = phone_number_id or settings.whatsapp_phone_number_id
    url = f"{WHATSAPP_API_BASE}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                    for b in buttons[:3]
                ]
            },
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def parse_incoming_message(payload: dict) -> Optional[dict]:
    """
    Parse a Meta webhook payload and extract the relevant message fields.
    Returns None if no actionable message is found.
    """
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None
        msg = messages[0]
        sender = msg.get("from")
        msg_type = msg.get("type")

        text = None
        if msg_type == "text":
            text = msg["text"]["body"]
        elif msg_type == "interactive":
            interactive = msg.get("interactive", {})
            if interactive.get("type") == "button_reply":
                text = interactive["button_reply"]["title"]
            elif interactive.get("type") == "list_reply":
                text = interactive["list_reply"]["title"]
        elif msg_type == "button":
            text = msg["button"]["text"]

        if not text or not sender:
            return None

        return {
            "sender": f"+{sender}",
            "text": text,
            "message_id": msg.get("id"),
            "timestamp": msg.get("timestamp"),
        }
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return None
