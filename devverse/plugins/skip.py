# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


from pyrogram import filters, types

from devverse import anon, app, db, lang
from devverse.helpers import can_manage_vc, utils

@app.on_message(filters.command(["skip", "next"]) & filters.group & ~app.bl_users)
@lang.language()
async def _skip(_, m: types.Message):

    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    await anon.play_next(m.chat.id)
    await utils.action_log("⏭ SKIPPED STREAM", m)
    await db.add_audit_log("SKIPPED TRACK", m.from_user.id, m.chat.id)
    
    await m.reply_text(m.lang["play_skipped"].format(m.from_user.mention))


