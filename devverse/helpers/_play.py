# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


import asyncio
from pyrogram import enums, errors, types, raw
from devverse import app, config, db, logger, queue, yt
from devverse.helpers import utils


def checkUB(play):
    async def wrapper(_, m: types.Message):
        if not m.from_user:
            return await m.reply_text(m.lang["play_user_invalid"])

        chat_id = m.chat.id
        if m.chat.type != enums.ChatType.SUPERGROUP:
            await m.reply_text(m.lang["play_chat_invalid"])
            return await app.leave_chat(chat_id)

        args = m.command[1:]
        flags = [arg for arg in args if arg.startswith("-")]
        query_parts = [arg for arg in args if not arg.startswith("-")]

        if not m.reply_to_message and not query_parts:
            return await m.reply_text(m.lang["play_usage"])

        if len(queue.get_queue(chat_id)) >= config.QUEUE_LIMIT:
            return await m.reply_text(m.lang["play_queue_full"].format(config.QUEUE_LIMIT))

        force = m.command[0].endswith("force") or "-f" in flags
        video = (m.command[0][0] == "v" or "-v" in flags) and config.VIDEO_PLAY
        url = utils.get_url(m)
        if url and yt.invalid(url):
            return await m.reply_text(m.lang["play_not_found"].format(config.SUPPORT_CHAT))
        m3u8 = url and not yt.valid(url)

        play_mode = await db.get_play_mode(chat_id)
        if play_mode or force:
            adminlist = await db.get_admins(chat_id)
            if (
                m.from_user.id not in adminlist
                and not await db.is_auth(chat_id, m.from_user.id)
                and not m.from_user.id in app.sudoers
            ):
                return await m.reply_text(m.lang["play_admin"])

        if chat_id not in db.active_calls:
            # Try to start VC if not active
            try:
                await app.invoke(
                    raw.functions.phone.CreateGroupCall(
                        peer=await app.resolve_peer(chat_id),
                        random_id=app.rnd_id(),
                    )
                )
                logger.info(f"Started Voice Chat in {chat_id}")
            except Exception:
                pass

            client = await db.get_client(chat_id)
            try:
                member = await app.get_chat_member(chat_id, client.id)
                if member.status in [
                    enums.ChatMemberStatus.BANNED,
                    enums.ChatMemberStatus.RESTRICTED,
                ]:
                    try:
                        await app.unban_chat_member(
                            chat_id=chat_id, user_id=client.id
                        )
                    except Exception:
                        return await m.reply_text(
                            m.lang["play_banned"].format(
                                app.name,
                                client.id,
                                client.mention,
                                f"@{client.username}" if client.username else None,
                            )
                        )
            except errors.ChatAdminRequired:
                return await m.reply_text(m.lang["admin_required"])
            except (errors.UserNotParticipant, errors.exceptions.bad_request_400.UserNotParticipant):
                if m.chat.username:
                    invite_link = m.chat.username
                    try:
                        await client.resolve_peer(invite_link)
                    except Exception:
                        pass
                else:
                    try:
                        invite_link = (await app.get_chat(chat_id)).invite_link
                        if not invite_link:
                            invite_link = await app.export_chat_invite_link(chat_id)
                    except errors.ChatAdminRequired:
                        return await m.reply_text(m.lang["admin_required"])
                    except Exception as ex:
                        return await m.reply_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )

                umm = await m.reply_text(m.lang["play_invite"].format(app.name))
                await asyncio.sleep(2)
                try:
                    await client.join_chat(invite_link)
                except errors.UserAlreadyParticipant:
                    pass
                except errors.InviteRequestSent:
                    await asyncio.sleep(2)
                    try:
                        await app.approve_chat_join_request(chat_id, client.id)
                    except errors.HideRequesterMissing:
                        pass
                    except Exception as ex:
                        return await umm.edit_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )
                except Exception as ex:
                    logger.error(f"Error joining chat - {chat_id}: {ex}")
                    return await umm.edit_text(
                        m.lang["play_invite_error"].format(type(ex).__name__)
                    )

                await umm.delete()
                await client.resolve_peer(chat_id)

        if await db.get_cmd_delete(chat_id):
            try:
                await m.delete()
            except Exception:
                pass

        return await play(_, m, force, m3u8, video, url)

    return wrapper

