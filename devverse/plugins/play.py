# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee — by @Delete_ee

import asyncio
from pathlib import Path

from pyrogram import filters, types

from devverse import anon, app, config, db, lang, queue, tg, yt
from devverse.helpers import buttons, status, utils
from devverse.helpers._play import checkUB


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    text = "<blockquote expandable>"
    for track in tracks:
        pos = queue.add(chat_id, track)
        text += f"<b>{pos}.</b> {track.title}\n"
    text = text[:1948] + "</blockquote>"
    return text


@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
) -> None:
    if not m.from_user:
        return

    # Check if user is manually restricted from using the bot
    if await db.is_restricted(m.from_user.id):
        return await m.reply_text(
            "🚫 **You are restricted** from using this bot.\n"
            "Contact the bot owner for assistance."
        )

    sent = await m.reply_text("🔍")
    asyncio.create_task(status.start(m.chat.id, sent))
    file = None
    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []

    # Update user & group info in DB for stats
    try:
        await db.update_user_info(
            m.from_user.id,
            username=m.from_user.username,
            first_name=m.from_user.first_name,
            last_name=m.from_user.last_name,
            is_bot=m.from_user.is_bot,
        )
        await db.update_group_info(
            m.chat.id,
            title=m.chat.title,
            username=getattr(m.chat, "username", None),
            member_count=getattr(m.chat, "members_count", 0),
            description=getattr(m.chat, "description", None),
        )
    except Exception:
        pass

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif m3u8:
        file = await tg.process_m3u8(url, sent.id, video)

    elif url:
        if "playlist" in url:
            pl_limit = 50 if await db.is_premium(m.chat.id) else config.PLAYLIST_LIMIT
            tracks = await yt.playlist(
                pl_limit, mention, url, video
            )

            if not tracks:
                await status.stop(m.chat.id, sent)
                return await m.reply_text(m.lang["playlist_error"])

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)

        if not file:
            await status.stop(m.chat.id, sent)
            return await m.reply_text(m.lang["play_not_found"].format(config.SUPPORT_CHAT))

    elif len(m.command) >= 2:
        # Drop -f / -v flags from the search query
        query = " ".join(arg for arg in m.command[1:] if not arg.startswith("-"))
        if not query:
            await status.stop(m.chat.id, sent)
            return await m.reply_text(m.lang["play_usage"])
        file = await yt.search(query, sent.id, video=video)
        if not file:
            await status.stop(m.chat.id, sent)
            return await m.reply_text(m.lang["play_not_found"].format(config.SUPPORT_CHAT))

    if not file:
        await status.stop(m.chat.id, sent)
        return await m.reply_text(m.lang["play_usage"])

    is_prem = await db.is_premium(m.chat.id)
    dl = config.DURATION_LIMIT if not is_prem else 99999
    if file.duration_sec > dl:
        await status.stop(m.chat.id, sent)
        return await m.reply_text(m.lang["play_duration_limit"].format(dl // 60))

    # Log to LOGGER group if enabled
    if await db.is_logger():
        await utils.play_log(m, sent.link, file.title, file.duration)

    # Download file to local downloads/ folder (ALWAYS local — no cloud upload)
    if not file.file_path and not media:
        if not Path("downloads").exists():
            Path("downloads").mkdir()
            
        expected_exts = utils.VIDEO_EXTS if video else utils.AUDIO_EXTS
        cached = sorted(
            (
                p
                for p in Path("downloads").glob(f"{file.id}.*")
                if not utils.is_download_fragment(p.name)
                and p.suffix.lower() in expected_exts
            ),
            # Prefer fully-converted files (.mp3) over raw fallbacks (.webm)
            key=lambda p: p.suffix.lower() != ".mp3",
        )
        if cached:
            file.file_path = str(cached[0])
        else:
            file.file_path = await yt.download(file.id, video=video)
            if not file.file_path:
                await status.stop(m.chat.id, sent)
                return await m.reply_text(
                    "❌ **Download Failed!**\n\n"
                    "YouTube blocked or restricted this video.\n"
                    "**Reasons:** Age-restricted · Geo-blocked · Private video\n\n"
                    f"Please try another song or contact [support]({config.SUPPORT_CHAT})."
                )

    # Register local file path for 30-min auto-cleanup tracking
    if file.file_path and not media:
        try:
            await db.register_file(
                song_id=file.id,
                storage_path=file.file_path,
                public_url="local",
                chat_id=m.chat.id,
                song_name=file.title,
            )
        except Exception:
            pass

    try:
        await db.log_song_request(
            user_id=m.from_user.id,
            username=m.from_user.username or "Unknown",
            first_name=m.from_user.first_name or "Unknown",
            chat_id=m.chat.id,
            chat_title=m.chat.title or "Unknown",
            song_name=file.title,
            song_link=getattr(file, "url", None),
            duration=file.duration,
        )
    except Exception:
        pass

    await db.add_audit_log(f"STREAM: {file.title}", m.from_user.id, m.chat.id)
    file.user = mention

    await status.stop(m.chat.id, sent, delete=False)
    if force:
        queue.force_add(m.chat.id, file)
    else:
        position = queue.add(m.chat.id, file)

        if position != 0 or await db.get_call(m.chat.id):
            await status.stop(m.chat.id, sent)
            msg = await m.reply_text(
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention,
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id, file.id, m.lang["play_now"]
                ),
            )
            if tracks:
                added = playlist_to_queue(m.chat.id, tracks)
                await app.send_message(
                    chat_id=m.chat.id,
                    text=m.lang["playlist_queued"].format(len(tracks)) + added,
                )
            return

    await anon.play_media(chat_id=m.chat.id, message=sent, media=file)
    if not tracks:
        return
    added = playlist_to_queue(m.chat.id, tracks)
    await app.send_message(
        chat_id=m.chat.id,
        text=m.lang["playlist_queued"].format(len(tracks)) + added,
    )

