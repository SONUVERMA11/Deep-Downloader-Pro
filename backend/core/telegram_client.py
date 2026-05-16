"""
DEEP DOWNLOADR — Telegram Client
Telethon integration with auth, media browsing, downloading,
and the 5-method smart resume system with .deepdl sidecar files.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("deep-downloadr.telegram")

APP_DIR = Path.home() / ".deep-downloadr"
SESSION_DIR = APP_DIR / "telegram"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class TelegramClient:
    """Telethon-based Telegram client for media browsing and downloading."""

    def __init__(self):
        self.client = None
        self.api_id: int | None = None
        self.api_hash: str | None = None
        self.phone: str | None = None
        self._connected = False

    async def connect(self, api_id: int, api_hash: str, phone: str) -> dict[str, Any]:
        """Initialize Telethon client and send OTP."""
        from telethon import TelegramClient as TC

        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone

        session_path = str(SESSION_DIR / f"session_{phone.replace('+', '')}")
        self.client = TC(session_path, api_id, api_hash)
        await self.client.connect()

        if not await self.client.is_user_authorized():
            await self.client.send_code_request(phone)
            return {"status": "otp_sent", "phone": phone}

        self._connected = True
        me = await self.client.get_me()
        return {"status": "connected", "user": me.first_name, "phone": phone}

    async def verify_otp(self, code: str, password: str | None = None) -> dict[str, Any]:
        """Verify OTP code and optional 2FA password."""
        from telethon.errors import SessionPasswordNeededError

        try:
            await self.client.sign_in(self.phone, code)
        except SessionPasswordNeededError:
            if password:
                await self.client.sign_in(password=password)
            else:
                return {"status": "2fa_required"}

        self._connected = True
        me = await self.client.get_me()
        return {"status": "connected", "user": me.first_name}

    async def get_dialogs(self) -> list[dict[str, Any]]:
        """Get all chats, channels, and groups."""
        from telethon.tl.types import Channel, Chat, User

        dialogs = await self.client.get_dialogs(limit=200)
        result = []
        for d in dialogs:
            entity = d.entity
            dialog_type = "private"
            member_count = 0

            if isinstance(entity, Channel):
                dialog_type = "channel" if entity.broadcast else "group"
                member_count = getattr(entity, 'participants_count', 0) or 0
            elif isinstance(entity, Chat):
                dialog_type = "group"
                member_count = getattr(entity, 'participants_count', 0) or 0
            elif isinstance(entity, User):
                if entity.bot:
                    dialog_type = "bot"

            result.append({
                "id": d.id,
                "name": d.name or "Unknown",
                "type": dialog_type,
                "member_count": member_count,
                "unread_count": d.unread_count,
            })

        return result

    async def get_media(
        self,
        chat_id: int,
        media_type: str = "all",
        limit: int = 100,
        offset_id: int = 0,
    ) -> list[dict[str, Any]]:
        """Get media messages from a chat."""
        from telethon.tl.types import (
            InputMessagesFilterDocument,
            InputMessagesFilterPhotos,
            InputMessagesFilterVideo,
            InputMessagesFilterMusic,
            InputMessagesFilterGif,
        )

        filter_map = {
            "video": InputMessagesFilterVideo,
            "photo": InputMessagesFilterPhotos,
            "audio": InputMessagesFilterMusic,
            "document": InputMessagesFilterDocument,
            "gif": InputMessagesFilterGif,
        }

        kwargs: dict[str, Any] = {
            "entity": chat_id,
            "limit": limit,
            "offset_id": offset_id,
        }

        if media_type != "all" and media_type in filter_map:
            kwargs["filter"] = filter_map[media_type]()

        messages = await self.client.get_messages(**kwargs)
        result = []

        for msg in messages:
            if not msg.media:
                continue

            file_name = ""
            file_size = 0
            mime_type = ""
            file_unique_id = ""

            if hasattr(msg.media, "document") and msg.media.document:
                doc = msg.media.document
                file_size = doc.size
                mime_type = doc.mime_type
                file_unique_id = str(doc.id)
                for attr in doc.attributes:
                    if hasattr(attr, "file_name"):
                        file_name = attr.file_name
                        break
            elif hasattr(msg.media, "photo") and msg.media.photo:
                photo = msg.media.photo
                file_unique_id = str(photo.id)
                mime_type = "image/jpeg"
                file_name = f"photo_{photo.id}.jpg"

            if not file_name:
                file_name = f"file_{msg.id}"

            result.append({
                "message_id": msg.id,
                "file_name": file_name,
                "file_size": file_size,
                "mime_type": mime_type,
                "file_unique_id": file_unique_id,
                "date": msg.date.isoformat() if msg.date else "",
                "sender": getattr(msg.sender, "first_name", "") if msg.sender else "",
                "caption": msg.text or "",
            })

        return result

    async def download_media(
        self,
        chat_id: int,
        message_id: int,
        output_path: str,
        progress_callback: Any = None,
    ) -> str:
        """Download a media file with .deepdl sidecar for resume support."""
        msg = await self.client.get_messages(chat_id, ids=message_id)
        if not msg or not msg.media:
            raise ValueError("Message has no media")

        # Determine file info
        file_name = ""
        file_size = 0
        file_unique_id = ""

        if hasattr(msg.media, "document") and msg.media.document:
            doc = msg.media.document
            file_size = doc.size
            file_unique_id = str(doc.id)
            for attr in doc.attributes:
                if hasattr(attr, "file_name"):
                    file_name = attr.file_name
                    break
        elif hasattr(msg.media, "photo"):
            file_unique_id = str(msg.media.photo.id)
            file_name = f"photo_{msg.media.photo.id}.jpg"

        if not file_name:
            file_name = f"file_{message_id}"

        os.makedirs(output_path, exist_ok=True)
        full_path = os.path.join(output_path, file_name)
        sidecar_path = full_path + ".deepdl"

        # Write initial sidecar
        sidecar_data = {
            "schema": "deepdl_v1",
            "source": "telegram",
            "chat_id": chat_id,
            "message_id": message_id,
            "file_unique_id": file_unique_id,
            "file_name": file_name,
            "mime_type": getattr(msg.media, "document", None) and msg.media.document.mime_type or "",
            "expected_size": file_size,
            "bytes_written": 0,
            "progress_pct": 0,
            "sha256_partial": "",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_written": datetime.now(timezone.utc).isoformat(),
            "destination": output_path,
            "app_version": "DEEP DOWNLOADR 1.0.0",
        }

        last_sidecar_update = 0

        async def _progress(current, total):
            nonlocal last_sidecar_update
            now = time.time()
            pct = current / max(total, 1) * 100

            # Update sidecar every 5 seconds
            if now - last_sidecar_update >= 5:
                sidecar_data["bytes_written"] = current
                sidecar_data["progress_pct"] = round(pct, 1)
                sidecar_data["last_written"] = datetime.now(timezone.utc).isoformat()
                with open(sidecar_path, "w") as f:
                    json.dump(sidecar_data, f, indent=2)
                last_sidecar_update = now

            if progress_callback:
                await progress_callback(pct)

        # Download
        result_path = await self.client.download_media(
            msg, file=full_path, progress_callback=_progress
        )

        # Remove sidecar on success
        if os.path.exists(sidecar_path):
            os.remove(sidecar_path)

        logger.info(f"Telegram download complete: {result_path}")
        return str(result_path)

    async def disconnect(self) -> None:
        if self.client:
            await self.client.disconnect()
            self._connected = False


# Global client instance
_client: TelegramClient | None = None

def get_client() -> TelegramClient:
    global _client
    if _client is None:
        _client = TelegramClient()
    return _client
