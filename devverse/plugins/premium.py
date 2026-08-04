# -*- coding: utf-8 -*-
from pyrogram import filters, types

from devverse import app, config, db, lang


@app.on_message(filters.command("premium") & filters.group & ~app.bl_users)
@lang.language()
async def premium_hndlr(_, m: types.Message):
    if not m.from_user:
        return

    if await db.is_premium(m.chat.id):
        text = (
            "🌟 **This group is PREMIUM!**\n\n"
            "**Benefits:**\n"
            "• Unlimited duration limit\n"
            "• Higher playlist limit (50)\n"
            "• Unlimited queue size\n"
            "• Priority support"
        )
    else:
        text = (
            "💎 **Premium Features**\n\n"
            "Upgrade your group for:\n"
            "• No duration limits\n"
            "• Playlist limit: 50 tracks\n"
            "• Unlimited queue\n"
            "• Priority support\n\n"
            f"Contact [Owner](https://t.me/{config.OWNER_USERNAME}) to purchase."
        )
    await m.reply_text(text, disable_web_page_preview=True)

