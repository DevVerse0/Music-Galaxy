# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee — by @Delete_ee

import asyncio
from pyrogram import enums, filters, types

from devverse import app, config, db, lang
from devverse.helpers import buttons, utils


@app.on_message(filters.command(["commands"]) & ~app.bl_users)
@lang.language()
async def _commands(_, m: types.Message):
    await m.reply_text(
        text=m.lang["help_menu"],
        reply_markup=buttons.help_markup(m.lang),
        quote=True,
    )


@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    await m.reply_text(
        text=m.lang["help_menu"],
        reply_markup=buttons.help_markup(m.lang),
        quote=True,
    )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    if not message.from_user:
        return

    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        await db.notify_user(message.from_user.id)
        return await message.reply_text(message.lang["bl_user_notify"])

    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    private = message.chat.type == enums.ChatType.PRIVATE
    uname = message.from_user.username or message.from_user.first_name
    _text = (
        message.lang["start_pm"].format(uname, app.name or "Music Galaxy")
        if private
        else message.lang["start_gp"].format(app.name or "Music Galaxy")
    )

    key = buttons.start_key(message.lang, private)
    try:
        await message.reply_photo(
            photo=config.START_IMG,
            caption=_text,
            reply_markup=key,
            quote=not private,
        )
    except Exception:
        await message.reply_text(
            text=_text,
            reply_markup=key,
            quote=not private,
        )

    if private:
        if await db.is_user(message.from_user.id):
            return
        await utils.send_log(message)
        await db.add_user(message.from_user.id)
        # Store user info for dashboard stats
        try:
            await db.update_user_info(
                message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                is_bot=message.from_user.is_bot,
            )
        except Exception:
            pass
    else:
        if await db.is_chat(message.chat.id):
            return
        await utils.send_log(message, True)
        await db.add_chat(message.chat.id)
        try:
            await db.update_group_info(
                message.chat.id,
                title=message.chat.title,
                username=getattr(message.chat, "username", None),
                member_count=getattr(message.chat, "members_count", 0),
                description=getattr(message.chat, "description", None),
            )
        except Exception:
            pass


@app.on_message(filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    admin_only = await db.get_play_mode(message.chat.id)
    cmd_delete = await db.get_cmd_delete(message.chat.id)
    _language = await db.get_lang(message.chat.id)
    await message.reply_text(
        text=message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, cmd_delete, _language, message.chat.id
        ),
        quote=True,
    )


@app.on_message(filters.new_chat_members, group=7)
@lang.language()
async def _new_member(_, message: types.Message):
    if message.chat.type != enums.ChatType.SUPERGROUP:
        return await message.chat.leave()

    await asyncio.sleep(3)
    for member in message.new_chat_members:
        if member.id == app.id:
            if await db.is_chat(message.chat.id):
                return
            await utils.send_log(message, True)
            await db.add_chat(message.chat.id)
            try:
                await db.update_group_info(
                    message.chat.id,
                    title=message.chat.title,
                    username=getattr(message.chat, "username", None),
                    member_count=getattr(message.chat, "members_count", 0),
                    description=getattr(message.chat, "description", None),
                )
            except Exception:
                pass

