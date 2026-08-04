# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee — by @Delete_ee

import re
import time
import asyncio

from pyrogram import enums, errors, filters, types

from devverse import anon, app, config, db, lang, queue, tg, yt
from devverse.helpers import admin_check, buttons, can_manage_vc, utils


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    action, chat_id = args[1], int(args[2])
    qaction = len(args) == 4
    user = query.from_user.mention

    if not await db.get_call(chat_id):
        try:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        except errors.QueryIdInvalid:
            try:
                await query.message.delete()
            except Exception:
                pass
            return

    if action == "status":
        return await query.answer()

    if getattr(config, "MAINTENANCE", False) and query.from_user.id != config.OWNER_ID:
        return await query.answer(
            "🔧 Bot is under maintenance. Please try again later.", show_alert=True
        )

    # Each branch calls query.answer exactly once (fix for button errors)
    reply = ""
    status = None

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(query.lang["play_already_paused"], show_alert=True)
        await query.answer(query.lang["processing"], show_alert=True)
        await anon.pause(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["paused"], False)
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        await query.answer(query.lang["processing"], show_alert=True)
        await anon.resume(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["playing"], True)
            )
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await query.answer(query.lang["processing"], show_alert=True)
        await anon.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.answer(query.lang["play_expired"], show_alert=True)
        await query.answer(query.lang["processing"], show_alert=True)
        m_id = queue.get_current(chat_id).message_id
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except Exception:
            pass
        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        return await anon.play_media(chat_id, msg, media)

    elif action == "replay":
        await query.answer(query.lang["processing"], show_alert=True)
        media = queue.get_current(chat_id)
        media.user = user
        await anon.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action == "stop":
        await query.answer(query.lang["processing"], show_alert=True)
        await anon.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    elif action == "seek_forward":
        media = queue.get_current(chat_id)
        if not media or not media.duration_sec:
            return await query.answer("❌ Cannot seek this stream.", show_alert=True)
        start_from = (getattr(media, 'time', 0) or 0) + 10
        if start_from + 5 > media.duration_sec:
            return await query.answer("⚠️ Already near the end.", show_alert=True)
        media.time = start_from
        await anon.play_media(chat_id, query.message, media, start_from)
        return await query.answer(f"⏩ Seeked to {start_from}s")

    elif action == "seek_back":
        media = queue.get_current(chat_id)
        if not media or not media.duration_sec:
            return await query.answer("❌ Cannot seek this stream.", show_alert=True)
        start_from = max(1, (getattr(media, 'time', 0) or 0) - 10)
        media.time = start_from
        await anon.play_media(chat_id, query.message, media, start_from)
        return await query.answer(f"⏪ Seeked to {start_from}s")

    elif action == "timer":
        await query.answer("⏱️ Opening timer...")
        media = queue.get_current(chat_id)
        if not media:
            return
        from devverse import anon as anon_inst
        try:
            elapsed = int(time() - anon_inst.start_times.get(chat_id, time()))
        except Exception:
            elapsed = 0
        total = media.duration_sec or 0
        pos = min(elapsed, total)
        bar_len = 12
        filled = int((pos / total) * bar_len) if total > 0 else 0
        bar = "━" * filled + "░" * (bar_len - filled)
        timer_text = f"⏱️ **Live Timer**\n\n{utils.format_time(pos)} {bar} {utils.format_time(total)}"
        try:
            timer_msg = await app.send_message(chat_id, timer_text)
        except errors.FloodWait as e:
            await asyncio.sleep(e.value)
            timer_msg = await app.send_message(chat_id, timer_text)
        # Cancel old timer popup if exists
        old = anon_inst.timer_popups.get(chat_id)
        if old:
            try:
                anon_inst.timer_popups[chat_id]["task"].cancel()
                await app.delete_messages(chat_id, int(old["msg_id"]))
            except Exception:
                pass
        # Start auto-update task
        task = asyncio.create_task(
            anon_inst._update_timer_popup(chat_id, timer_msg.id, media)
        )
        anon_inst.timer_popups[chat_id] = {"msg_id": timer_msg.id, "task": task}
        return

    else:
        return await query.answer("Unknown action.", show_alert=True)

    if not reply:
        return

    try:
        if action in ["skip", "replay", "stop"]:
            await query.message.reply_text(reply, quote=False)
            await query.message.delete()
            return

        # Get current message text safely
        curr_text = ""
        try:
            curr_text = query.message.caption.html or ""
        except Exception:
            pass
        if not curr_text:
            try:
                curr_text = query.message.text.html or ""
            except Exception:
                pass

        mtext = re.sub(
            r"\n\n<blockquote>.*?</blockquote>",
            "",
            curr_text,
            flags=re.DOTALL,
        )
        keyboard = buttons.controls(chat_id, status=status)
        if query.message.photo or query.message.video:
            await query.edit_message_caption(
                f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
            )
        else:
            await query.edit_message_text(
                f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
            )
    except Exception:
        pass


@app.on_callback_query(filters.regex("help") & ~app.bl_users)
@lang.language()
async def _help(_, query: types.CallbackQuery):
    data = query.data.split()
    if len(data) == 1:
        # If it's just 'help', it should open the help menu (edit current message)
        # However, the userbot/bot might want to redirect to PM if in group
        if query.message.chat.type != enums.ChatType.PRIVATE:
            return await query.answer(url=f"https://t.me/{app.username}?start=help")
        
        # In PM, show the root help menu
        text = query.lang["help_menu"]
        markup = buttons.help_markup(query.lang)
        try:
            if query.message.photo or query.message.video:
                return await query.edit_message_caption(caption=text, reply_markup=markup)
            return await query.edit_message_text(text=text, reply_markup=markup)
        except Exception:
            return await query.answer()

    await query.answer()

    if data[1] == "close":
        try:
            await query.message.delete()
            return await query.message.reply_to_message.delete()
        except Exception:
            return

    if data[1] == "back":
        text = query.lang["help_menu"]
        markup = buttons.help_markup(query.lang)
    else:
        text = query.lang[f"help_{data[1]}"]
        markup = buttons.help_markup(query.lang, True)

    try:
        if query.message.photo or query.message.video:
            await query.edit_message_caption(caption=text, reply_markup=markup)
        else:
            await query.edit_message_text(text=text, reply_markup=markup)
    except Exception:
        pass


@app.on_callback_query(filters.regex("^settings$|^settings ") & ~app.bl_users)
@lang.language()
@admin_check
async def _settings_cb(_, query: types.CallbackQuery):
    cmd = query.data.split()

    # Extract chat_id: from cmd[2] if present, else from message chat
    # Formats: "settings"  |  "settings noop <chat_id>"  |  "settings <action> <chat_id>"
    if len(cmd) >= 3:
        try:
            chat_id = int(cmd[2])
        except (ValueError, IndexError):
            chat_id = query.message.chat.id
    else:
        chat_id = query.message.chat.id

    action = cmd[1] if len(cmd) >= 2 else None

    # Label buttons are "noop" — just acknowledge with specific message
    if action == "noop":
        try:
            return await query.answer("ℹ️ Tap the ✅ or ❌ button to toggle this setting.", show_alert=False)
        except Exception:
            return await query.answer()

    _admin = await db.get_play_mode(chat_id)
    _delete = await db.get_cmd_delete(chat_id)
    _language = await db.get_lang(chat_id)

    if action == "delete":
        await query.answer("Processing...", show_alert=False)
        _delete = not _delete
        await db.set_cmd_delete(chat_id, _delete)
    elif action == "play":
        await query.answer("Processing...", show_alert=False)
        _admin = not _admin
        await db.set_play_mode(chat_id, _admin)
    else:
        # For entry onto settings from a command, just answer empty
        await query.answer()

    reply_m = buttons.settings_markup(query.lang, _admin, _delete, _language, chat_id)

    try:
        chat_title = getattr(query.message.chat, "title", None) or "Private Chat"
    except Exception:
        chat_title = "Private Chat"

    text = query.lang["start_settings"].format(chat_title)

    try:
        if query.message.photo or query.message.video:
            await query.edit_message_caption(caption=text, reply_markup=reply_m)
        else:
            await query.edit_message_text(text=text, reply_markup=reply_m)
    except Exception:
        pass


