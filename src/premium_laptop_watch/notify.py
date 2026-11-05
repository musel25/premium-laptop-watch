"""Telegram delivery restricted to the independently verified personal chat."""

import json
import shlex
from pathlib import Path

import httpx


class DeliveryError(RuntimeError):
    pass


class Telegram:
    def __init__(self, recipient_path: Path, secrets_path: Path, transport=None):
        recipient = json.loads(recipient_path.read_text())
        self.chat_id = recipient.get("chat_id")
        if (
            not isinstance(self.chat_id, int)
            or self.chat_id <= 0
            or not recipient.get("verification_code")
            or not recipient.get("test_message_id")
        ):
            raise DeliveryError("verified private recipient is missing")
        settings = {}
        for line in secrets_path.read_text().splitlines():
            parts = shlex.split(line, comments=True)
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    settings[key] = value
        self.token = settings.get("TGVMAX_TELEGRAM_TOKEN", "")
        if not self.token:
            raise DeliveryError("Telegram token is missing")
        self.transport = transport

    def send(self, text: str) -> int:
        try:
            with httpx.Client(timeout=20, transport=self.transport) as client:
                response = client.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text[:4000],
                        "link_preview_options": {"is_disabled": True},
                    },
                )
                response.raise_for_status()
                data = response.json()
            message = data.get("result", {})
            chat = message.get("chat", {})
            if (
                not data.get("ok")
                or chat.get("id") != self.chat_id
                or chat.get("type") != "private"
                or not isinstance(message.get("message_id"), int)
            ):
                raise DeliveryError(
                    "Telegram did not confirm the intended private recipient"
                )
            return message["message_id"]
        except (httpx.HTTPError, ValueError, TypeError):
            raise DeliveryError(
                "Telegram delivery failed; no confirmed receipt"
            ) from None
