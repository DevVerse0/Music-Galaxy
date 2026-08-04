# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


import os
import time
import asyncio

from pyrogram import enums, errors, filters, types

from devverse import anon, app, config, db, lang, logger, queue, tasks, userbot, yt
from devverse.helpers import buttons


@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await anon.stop(m.chat.id)


async def auto_leave():
    while True:
        await asyncio.sleep(120)
        for ub in userbot.clients:
            try:
                chats = [dialog.chat.id async for dialog in ub.get_dialogs()
                            if dialog.chat.type in [
                                enums.ChatType.GROUP, enums.ChatType.SUPERGROUP,
                            ]][-20:]
                for chat in chats:
                    if chat in [app.logger, -1001686672798, -1001549206010]:
                        continue
                    if chat in db.active_calls:
                        continue
                    await ub.leave_chat(chat)
                    await asyncio.sleep(7)
            except asyncio.CancelledError:
                raise
            except Exception:
                continue


async def track_time():
    while True:
        await asyncio.sleep(1)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            media = queue.get_current(chat_id)
            if not media:
                continue
            media.time += 1


async def update_timer(length=10):
    while True:
        await asyncio.sleep(7)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            try:
                media = queue.get_current(chat_id)
                duration, message_id = media.duration_sec, media.message_id
                if not duration or not message_id or not media.time:
                    continue
                played = media.time
                remaining = duration - played
                pos = min(int((played / duration) * length), length - 1)
                timer = "\u2014" * pos + "\u25c9" + "\u2014" * (length - pos - 1)

                if remaining <= 30:
                    nxt = queue.get_next(chat_id, check=True)
                    if nxt and not nxt.file_path:
                        nxt.file_path = await yt.download(nxt.id, video=nxt.video)

                if remaining < 10:
                    remove = True
                else:
                    if config.THUMB_GEN:
                        timer = f"{time.strftime('%M:%S', time.gmtime(played))} | {timer} | -{time.strftime('%M:%S', time.gmtime(remaining))}"
                    else:
                        timer = None
                    remove = False

                if not timer and not remove:
                    # Update buttons every 10s even if no timer string (to sync pause/resume state)
                    if played % 10 != 0:
                        continue

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id, timer=timer, remove=remove
                    ),
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                pass


async def vc_watcher(sleep=15):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            client = await db.get_assistant(chat_id)
            media = queue.get_current(chat_id)
            participants = await client.get_participants(chat_id)
            if len(participants) < 2 and media.time > 30:
                _lang = await lang.get_lang(chat_id)
                try:
                    sent = await app.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=media.message_id,
                        reply_markup=buttons.controls(
                            chat_id=chat_id, status=_lang["stopped"], remove=True
                        ),
                    )
                    await anon.stop(chat_id)
                    await sent.reply_text(_lang["auto_left"])
                except errors.MessageIdInvalid:
                    pass


# ────────────────────────────────────────────────────────────────────────────
# LOCAL FILE CLEANUP  (deletes downloads/ files after 30 minutes)
# ────────────────────────────────────────────────────────────────────────────

async def local_file_cleanup():
    """Delete expired song files from local downloads/ folder every 30 minutes."""
    return  # Auto cleanup disabled by user request
    await asyncio.sleep(60)  # wait 1 min after startup before first run
    while True:
        try:
            now = time.time()
            expired_files = await db.get_file_registry(limit=200)
            for entry in expired_files:
                # Only delete if expired (expires_at = uploaded_at + 1800s)
                if entry.get("expires_at", 0) < now:
                    local_path = entry.get("storage_path", "")
                    # Only delete real local paths, skip placeholders / URLs
                    if local_path and local_path != "local" and not local_path.startswith("http"):
                        try:
                            if os.path.exists(local_path):
                                os.remove(local_path)
                                logger.info(f"🗑️ Auto-deleted expired file: {local_path}")
                        except Exception as e:
                            logger.debug(f"File delete failed ({local_path}): {e}")
                    # Always remove from registry
                    try:
                        await db.unregister_file(entry["song_id"])
                    except Exception:
                        pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(1800)


# ────────────────────────────────────────────────────────────────────────────
# BOT-NOT-ADMIN ALERT  (unique styled warning message)
# ────────────────────────────────────────────────────────────────────────────

_admin_alert_sent: set = set()

ADMIN_ALERT_TEXT = (
    "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u256e\n"
    "\u2502  \u26a0\ufe0f  <b>ADMIN PERMISSION NEEDED</b>   \u2502\n"
    "\u2570\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u256f\n\n"
    "\ud83e\udd16 <b>{bot}</b> is <u>not an admin</u> in this group!\n\n"
    "I need the following admin rights to work:\n"
    "  \u2022 \ud83d\udce2 <b>Manage Voice Chats</b>\n"
    "  \u2022 \ud83d\uddd1\ufe0f <b>Delete Messages</b>\n"
    "  \u2022 \ud83d\udc65 <b>Invite / Add Members</b>\n\n"
    "<i>Please promote me to admin, otherwise I cannot play music properly.</i>\n\n"
    "\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\u254c\n"
    "\ud83d\udc51 Owner: @{owner}"
)


async def _send_admin_alert(chat_id: int, chat_title: str):
    try:
        await app.send_message(
            chat_id,
            ADMIN_ALERT_TEXT.format(
                bot=app.name if hasattr(app, "name") else "Delete_ee",
                owner=config.OWNER_USERNAME,
            ),
        )
        await db.log_admin_alert(
            chat_id=chat_id,
            chat_title=chat_title,
            bot_id=app.id,
            bot_name=app.name if hasattr(app, "name") else "Delete_ee",
        )
    except Exception:
        pass


async def bot_admin_checker():
    """Scan all registered chats hourly — alert if bot is not admin."""
    await asyncio.sleep(120)
    while True:
        try:
            chats = await db.get_chats()
            for chat_id in chats:
                try:
                    member = await app.get_chat_member(chat_id, app.id)
                    is_admin = member.status in [
                        enums.ChatMemberStatus.ADMINISTRATOR,
                        enums.ChatMemberStatus.OWNER,
                    ]
                    if not is_admin and chat_id not in _admin_alert_sent:
                        _admin_alert_sent.add(chat_id)
                        chat = await app.get_chat(chat_id)
                        await _send_admin_alert(chat_id, chat.title or "Unknown")
                    elif is_admin:
                        _admin_alert_sent.discard(chat_id)
                except Exception:
                    pass
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(3600)


# ────────────────────────────────────────────────────────────────────────────
# ON JOIN: immediately check admin status
# ────────────────────────────────────────────────────────────────────────────

@app.on_message(filters.new_chat_members, group=21)
async def _check_admin_on_join(_, message: types.Message):
    await asyncio.sleep(5)
    for member in message.new_chat_members:
        if member.id == app.id:
            try:
                me = await app.get_chat_member(message.chat.id, app.id)
                is_admin = me.status in [
                    enums.ChatMemberStatus.ADMINISTRATOR,
                    enums.ChatMemberStatus.OWNER,
                ]
                if not is_admin:
                    _admin_alert_sent.add(message.chat.id)
                    await _send_admin_alert(
                        message.chat.id,
                        message.chat.title or "Unknown",
                    )
            except Exception:
                pass


# ────────────────────────────────────────────────────────────────────────────
# START TASKS
# ────────────────────────────────────────────────────────────────────────────

if config.AUTO_END:
    tasks.append(asyncio.create_task(vc_watcher()))
if config.AUTO_LEAVE:
    tasks.append(asyncio.create_task(auto_leave()))
tasks.append(asyncio.create_task(track_time()))
tasks.append(asyncio.create_task(update_timer()))
# tasks.append(asyncio.create_task(local_file_cleanup())) # Disabled by user
tasks.append(asyncio.create_task(bot_admin_checker()))

