# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# Advanced Spy System — by @Delete_ee

from datetime import datetime
from pyrogram import filters, types, enums
from devverse import app, db, config, logger


@app.on_message(app.spy_users, group=-1)
async def stalk_handler(client, message: types.Message):
    """
    Advanced spy/stalk system.
    Each spy target has a destination group_id stored in the DB.
    If dest_group_id == 0, use global LOGGER_ID.
    """
    if not message.from_user:
        return

    user = message.from_user
    chat = message.chat

    # Get destination for this specific spy target
    dest = await db.get_spy_dest(user.id)
    target_group = dest if dest else config.LOGGER_ID
    if not target_group:
        return

    # Build detailed spy log
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chat_type = str(chat.type).replace("ChatType.", "")
    msg_content = (
        message.text or
        message.caption or
        f"[{_media_type(message)}]"
    )

    log_text = (
        f"🕵️‍♂️ <b>SPY LOG</b>\n"
        f"{'─' * 30}\n"
        f"⏰ <b>Time:</b> <code>{now}</code>\n\n"
        f"👤 <b>Target User:</b>\n"
        f"  ├ <b>Name:</b> {user.mention}\n"
        f"  ├ <b>ID:</b> <code>{user.id}</code>\n"
        f"  ├ <b>Username:</b> @{user.username or 'none'}\n"
        f"  └ <b>Is Bot:</b> {'Yes' if user.is_bot else 'No'}\n\n"
        f"🏘️ <b>Source Chat:</b>\n"
        f"  ├ <b>Name:</b> {chat.title or 'Private DM'}\n"
        f"  ├ <b>ID:</b> <code>{chat.id}</code>\n"
        f"  ├ <b>Type:</b> <code>{chat_type}</code>\n"
        f"  └ <b>Username:</b> @{chat.username or 'none'}\n\n"
        f"💬 <b>Message:</b>\n"
        f"<blockquote>{msg_content[:1000]}</blockquote>\n"
    )

    if message.reply_to_message:
        rep = message.reply_to_message
        replied_text = (rep.text or rep.caption or f"[{_media_type(rep)}]")[:400]
        log_text += f"\n↩️ <b>Replying to:</b> <code>{rep.from_user.id if rep.from_user else '?'}</code>\n<blockquote>{replied_text}</blockquote>"

    try:
        # Try to forward original message first (for media), then send log
        await client.send_message(target_group, log_text, parse_mode=enums.ParseMode.HTML)

        # If it's media, try to forward devversemously
        if message.media:
            try:
                await message.copy(target_group)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Spy log delivery failed for {user.id} → {target_group}: {e}")


def _media_type(message: types.Message) -> str:
    """Get a human-readable media type label."""
    if message.photo:       return "📸 Photo"
    if message.video:       return "🎥 Video"
    if message.audio:       return "🎵 Audio"
    if message.voice:       return "🎤 Voice Note"
    if message.document:    return "📄 Document"
    if message.sticker:     return "🎭 Sticker"
    if message.animation:   return "🎞️ GIF/Animation"
    if message.video_note:  return "📹 Video Note"
    if message.location:    return "📍 Location"
    if message.contact:     return "👤 Contact"
    if message.poll:        return "📊 Poll"
    return "📦 Unknown Media"

