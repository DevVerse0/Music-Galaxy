# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


import time
import psutil

from pyrogram import filters, types
from devverse import app, anon, boot, config, lang, db
from devverse.helpers import buttons


@app.on_message(filters.command(["alive", "ping"]) & ~app.bl_users)
@lang.language()
async def _ping(_, m: types.Message):
    start = time.time()
    sent = await m.reply_text(m.lang["pinging"])
    get_time = lambda s: (lambda r: (f"{r[-1]}, " if r[-1][:-4] != "0" else "") + ":".join(reversed(r[:-1])))([f"{v}{u}" for v, u in zip([s%60, (s//60)%60, (s//3600)%24, s//86400], ["s", "m", "h", "days"])])
    uptime = get_time(int(time.time() - boot))
    latency = round((time.time() - start) * 1000, 2)
    await sent.edit_media(
        media=types.InputMediaPhoto(
            media=config.PING_IMG,
            caption=m.lang["ping_pong"].format(
                latency,
                uptime,
                psutil.cpu_percent(interval=0),
                psutil.virtual_memory().percent,
                psutil.disk_usage("/").percent,
                await anon.ping(),
            )
        ),
        reply_markup=buttons.ping_markup(m.lang["support"]),
    )


@app.on_message(filters.command(["stats"]) & ~app.bl_users)
@lang.language()
async def _stats(_, m: types.Message):
    sent = await m.reply_text(m.lang["stats_fetching"])
    
    users = len(await db.get_users())
    chats = len(await db.get_chats())
    
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    ram_mb = round(mem.used / (1024 * 1024), 2)
    disk_gb = round(disk.total / (1024 * 1024 * 1024), 2)

    if m.from_user.id in app.sudoers:
        text = m.lang["stats_sudo"].format(ram_mb, cpu, disk_gb)
    else:
        text = m.lang["stats_user"].format(app.name, users, chats)

    await sent.edit_text(text)

