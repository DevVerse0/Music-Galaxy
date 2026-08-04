# -*- coding: utf-8 -*-
import asyncio

from pyrogram import types


class Status:
    def __init__(self):
        self._tasks = {}

    async def start(self, chat_id: int, message: types.Message) -> None:
        frames = ["🔍", "🔎", "📥", "📤", "✅"]
        for frame in frames:
            try:
                await message.edit_text(frame)
                await asyncio.sleep(1.5)
            except Exception:
                break

    async def stop(self, chat_id: int, message: types.Message, delete: bool = True) -> None:
        if chat_id in self._tasks:
            self._tasks[chat_id].cancel()
            del self._tasks[chat_id]
        if delete:
            try:
                await message.delete()
            except Exception:
                pass

