# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


import os
import re

from pyrogram import enums, types

from devverse import app


class Utilities:
    # Expected final extensions for downloaded media (yt-dlp outputs).
    VIDEO_EXTS = (".mp4",)
    AUDIO_EXTS = (".mp3", ".webm", ".m4a", ".opus", ".ogg", ".flac", ".aac")

    def __init__(self):
        pass

    def format_eta(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d} min"
        else:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h}:{m:02d}:{s:02d} h"

    def format_size(self, bytes: int) -> str:
        if bytes >= 1024**3:
            return f"{bytes / 1024 ** 3:.2f} GB"
        elif bytes >= 1024**2:
            return f"{bytes / 1024 ** 2:.2f} MB"
        else:
            return f"{bytes / 1024:.2f} KB"

    def format_time(self, seconds: int) -> str:
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def to_seconds(self, time: str) -> int:
        try:
            if not time or not isinstance(time, str):
                return 0
            parts = [int(p) for p in time.strip().split(":") if p.isdigit()]
            if not parts:
                return 0
            return sum(value * 60**i for i, value in enumerate(reversed(parts)))
        except Exception:
            return 0


    def is_download_fragment(self, name: str) -> bool:
        """True for unfinished yt-dlp files (DASH fragments / temp files)."""
        name = os.path.basename(name)
        if name.lower().endswith((".part", ".ytdl", ".temp", ".tmp")):
            return True
        # yt-dlp DASH fragments look like: <id>.f251.webm / <id>.f395.mp4
        return bool(re.search(r"\.f\d+\.", name))

    def get_url(self, message_1: types.Message) -> str | None:
        link = None
        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            entities = message.entities or message.caption_entities or []

            for entity in entities:
                if entity.type == enums.MessageEntityType.TEXT_LINK:
                    link = entity.url
                    break
                elif entity.type == enums.MessageEntityType.URL:
                    text = message.text or message.caption
                    if not text:
                        continue
                    link = text[entity.offset: entity.offset + entity.length]
                    break

        if link:
            return link.split("&si")[0].split("?si")[0]
        return None


    async def extract_user(self, msg: types.Message) -> types.User | None:
        if msg.reply_to_message:
            return msg.reply_to_message.from_user

        if msg.entities:
            for e in msg.entities:
                if e.type == enums.MessageEntityType.TEXT_MENTION:
                    return e.user

        if msg.text:
            try:
                if m := re.search(r"@(\w{5,32})", msg.text):
                    return await app.get_users(m.group(0))
                if m := re.search(r"\b\d{6,15}\b", msg.text):
                    return await app.get_users(int(m.group(0)))
            except Exception:
                pass

        return None


    async def play_log(
        self,
        m: types.Message,
        link: str,
        title: str,
        duration: str,
    ) -> None:
        if m.chat.id == app.logger:
            return
        
        _text = (
            f"<b>🚨 NEW SONG PLAY ALERT</b>\n\n"
            f"<b>🏢 Group Info:</b>\n"
            f"  • Name: <code>{m.chat.title}</code>\n"
            f"  • ID: <code>{m.chat.id}</code>\n"
            f"  • Link: @{m.chat.username if getattr(m.chat, 'username', None) else 'Private'}\n\n"
            f"<b>👤 Target User:</b>\n"
            f"  • Name: {m.from_user.mention}\n"
            f"  • ID: <code>{m.from_user.id}</code>\n"
            f"  • Username: @{m.from_user.username if m.from_user.username else 'None'}\n\n"
            f"<b>🎵 Track Info:</b>\n"
            f"  • Title: <a href='{link}'>{title}</a>\n"
            f"  • Duration: <code>{duration}</code>\n"
        )
        try:
            await app.send_message(chat_id=app.logger, text=_text, disable_web_page_preview=True)
        except Exception:
            pass

    async def send_log(self, m: types.Message, chat: bool = False) -> None:
        try:
            if chat:
                user = m.from_user
                _text = (
                    f"<b>✅ NEW GROUP ACTIVATION</b>\n\n"
                    f"<b>🏢 Group:</b> <code>{m.chat.title}</code>\n"
                    f"<b>🆔 ID:</b> <code>{m.chat.id}</code>\n"
                    f"<b>👤 Added By:</b> {user.mention if user else 'devversemous'}\n"
                    f"<b>🆔 User ID:</b> <code>{user.id if user else 'Unknown'}</code>"
                )
            else:
                _text = (
                    f"<b>✅ NEW BOT USER</b>\n\n"
                    f"<b>👤 User:</b> {m.from_user.mention}\n"
                    f"<b>🆔 ID:</b> <code>{m.from_user.id}</code>\n"
                    f"<b>🌐 Username:</b> @{m.from_user.username if m.from_user.username else 'None'}"
                )
            await app.send_message(chat_id=app.logger, text=_text, disable_web_page_preview=True)
        except Exception:
            pass

    async def action_log(self, action: str, m: types.Message = None, extra: str = "") -> None:
        if not m or m.chat.id == app.logger:
            return
        
        _text = (
            f"<b>⚙️ BOT ACTION TRIGGERED</b>\n\n"
            f"<b>⚡ Action:</b> <code>{action}</code>\n"
            f"<b>🏢 Group:</b> <code>{m.chat.title}</code> (<code>{m.chat.id}</code>)\n"
            f"<b>👤 Triggered By:</b> {m.from_user.mention if m.from_user else 'Admin/System'}\n"
        )
        if extra:
            _text += f"\n<b>📝 Extra Details:</b> {extra}"
        
        try:
            await app.send_message(chat_id=app.logger, text=_text, disable_web_page_preview=True)
        except Exception:
            pass

