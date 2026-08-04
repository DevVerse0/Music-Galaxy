# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


import asyncio
from time import time
from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported, ConnectionError)
from pyrogram.errors import (ChatSendMediaForbidden, ChatSendPhotosForbidden,
                             MessageIdInvalid)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from devverse import (app, config, db, lang, logger,
                   queue, thumb, userbot, yt)
from devverse.helpers import Media, Track, buttons, status, utils


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        self.idle_tasks = {}
        self.timer_tasks = {}
        self.start_times = {}
        self.timer_popups = {}

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        return await client.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        return await client.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)
        
        # Cancel idle timer
        if chat_id in self.idle_tasks:
            self.idle_tasks[chat_id].cancel()
            del self.idle_tasks[chat_id]

        # Cancel progress timer
        if chat_id in self.timer_tasks:
            self.timer_tasks[chat_id].cancel()
            del self.timer_tasks[chat_id]
        self.start_times.pop(chat_id, None)

        # Cancel timer popup
        if chat_id in self.timer_popups:
            try:
                self.timer_popups[chat_id]["task"].cancel()
                await app.delete_messages(chat_id, int(self.timer_popups[chat_id]["msg_id"]))
            except Exception:
                pass
            del self.timer_popups[chat_id]

        try:
            await client.leave_call(chat_id, close=False)
        except Exception:
            pass

    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
    ) -> None:
        # Cancel idle timer if song starts
        if chat_id in self.idle_tasks:
            self.idle_tasks[chat_id].cancel()
            del self.idle_tasks[chat_id]

        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media)
            if isinstance(media, Track)
            else config.DEFAULT_THUMB
        ) if config.THUMB_GEN else None

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.MEDIUM,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if media.video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                await db.add_audit_log(f"STARTED PLAYING: {media.title[:20]}", chat_id=chat_id)
                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    media.duration,
                    media.user,
                )
                init_timer = f"⏳ 00:00 {'░' * 12} {utils.format_time(media.duration_sec)}" if media.duration_sec else None
                keyboard = buttons.controls(chat_id, timer=init_timer)
                try:
                    if _thumb:
                        await message.edit_media(
                            media=InputMediaPhoto(
                                media=_thumb,
                                caption=text,
                            ),
                            reply_markup=keyboard,
                        )
                    else:
                        await message.edit_text(text, reply_markup=keyboard)
                except (ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid):
                    if _thumb:
                        sent = await app.send_photo(
                            chat_id=chat_id,
                            photo=_thumb,
                            caption=text,
                            reply_markup=keyboard,
                        )
                    else:
                        sent = await app.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=keyboard,
                        )
                    media.message_id = sent.id
            if media.duration_sec:
                self.start_times[chat_id] = time()
                self.timer_tasks[chat_id] = asyncio.create_task(
                    self._update_timer(chat_id, message, media)
                )
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self.play_next(chat_id)
        except (ConnectionError, ConnectionNotFound, TelegramServerError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])

    async def _update_timer(self, chat_id: int, message: Message, media) -> None:
        while chat_id in self.timer_tasks:
            elapsed = int(time() - self.start_times.get(chat_id, time()))
            total = media.duration_sec or 0
            if total <= 0:
                break
            pos = min(elapsed, total)
            bar_len = 12
            filled = int((pos / total) * bar_len)
            bar = "━" * filled + "░" * (bar_len - filled)
            timer_text = f"⏳ {utils.format_time(pos)} {bar} {utils.format_time(total)}"
            try:
                msg = await app.get_messages(chat_id, message.id)
                caption = msg.caption or msg.text or ""
                clean = caption.split("\n⏳")[0]
                keyboard = buttons.controls(chat_id, timer=timer_text)
                if msg.media:
                    await msg.edit_media(
                        InputMediaPhoto(media=msg.photo.file_id, caption=clean),
                        reply_markup=keyboard
                    )
                else:
                    await msg.edit_text(clean, reply_markup=keyboard)
            except Exception:
                pass
            await asyncio.sleep(10)

    async def _update_timer_popup(self, chat_id: int, msg_id: int, media) -> None:
        while chat_id in self.timer_popups:
            elapsed = int(time() - self.start_times.get(chat_id, time()))
            total = media.duration_sec or 0
            if total <= 0 or chat_id not in db.active_calls:
                break
            pos = min(elapsed, total)
            bar_len = 12
            filled = int((pos / total) * bar_len)
            bar = "━" * filled + "░" * (bar_len - filled)
            timer_text = f"⏱️ **Live Timer**\n\n{utils.format_time(pos)} {bar} {utils.format_time(total)}"
            try:
                msg = await app.get_messages(chat_id, msg_id)
                await msg.edit_text(timer_text)
            except Exception:
                break
            await asyncio.sleep(10)

    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return
        media = queue.get_current(chat_id)
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)

    async def play_next(self, chat_id: int) -> None:
        if loop := await db.get_loop(chat_id):
            await db.set_loop(chat_id, loop - 1)
            return await self.replay(chat_id)

        media = queue.get_next(chat_id)
        try:
            if media and media.message_id:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except Exception:
            pass

        if not media:
            if config.AUTO_LEAVE:
                # Start idle timer for 2 minutes
                self.idle_tasks[chat_id] = asyncio.create_task(self.idle_check(chat_id))
            return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text="📥")
        asyncio.create_task(status.start(chat_id, msg))
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
            if not media.file_path:
                await self.play_next(chat_id)
                return await msg.edit_text(
                    _lang["error_no_file"].format(config.SUPPORT_CHAT)
                )

        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)

    async def idle_check(self, chat_id: int):
        try:
            await asyncio.sleep(600) # 10 minutes idle time
            client = await db.get_assistant(chat_id)
            try:
                _lang = await lang.get_lang(chat_id)
                await client.leave_call(chat_id)
                logger.info(f"Assistant left {chat_id} due to 10m idle.")
                await app.send_message(chat_id, _lang["auto_left"])
            except Exception:
                pass

        except asyncio.CancelledError:
            pass

    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)

    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")

