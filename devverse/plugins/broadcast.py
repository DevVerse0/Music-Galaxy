# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee

import asyncio
from pyrogram import filters, types, errors
from devverse import app, db, config, logger

@app.on_message(filters.command(["broadcast", "gcast"]) & filters.user(config.OWNER_ID))
async def _broadcast(_, m: types.Message):
    if m.reply_to_message:
        msg = m.reply_to_message
        text_to_send = None
    elif len(m.command) > 1:
        text_content = m.text or m.caption
        msg = m if m.media else text_content.split(None, 1)[1]
        text_to_send = text_content.split(None, 1)[1] if text_content else None
    elif m.media:
        msg = m
        text_to_send = ""
    else:
        return await m.reply_text("<b>Usage:</b>\nReply to a message OR <code>/broadcast text</code>")

    sent_msg = await m.reply_text("🚀 <b>Broadcasting...</b>")
    
    chats = await db.get_chats()
    users = await db.get_users()
    all_targets = list(set(chats + users))
    
    count = 0
    failed = 0
    
    for target in all_targets:
        try:
            if isinstance(msg, str):
                await app.send_message(target, msg)
            elif text_to_send is not None:
                await msg.copy(target, caption=text_to_send)
            else:
                await msg.copy(target)
            count += 1
            await asyncio.sleep(0.3) # Avoid flood
        except errors.FloodWait as e:
            await asyncio.sleep(e.value)
            if isinstance(msg, str):
                await app.send_message(target, msg)
            elif text_to_send is not None:
                await msg.copy(target, caption=text_to_send)
            else:
                await msg.copy(target)
            count += 1
        except Exception:
            failed += 1
            continue

    await sent_msg.edit_text(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"📨 <b>Sent to:</b> {count} targets\n"
        f"❌ <b>Failed:</b> {failed} targets"
    )
    
    # Log to logger
    try:
        await app.send_message(
            config.LOGGER_ID,
            f"📢 <b>Owner Broadcast</b>\n"
            f"👤 <b>By:</b> {m.from_user.mention}\n"
            f"✅ <b>Sent:</b> {count}\n"
            f"❌ <b>Failed:</b> {failed}"
        )
    except Exception:
        pass

