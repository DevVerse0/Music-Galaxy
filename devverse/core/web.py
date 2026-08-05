# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee — by @Delete_ee

import os
import time
import asyncio
import psutil
import uvicorn
from typing import Union, Optional
from datetime import datetime

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pyrogram.types import ChatPrivileges, ChatPermissions

from devverse import db, config, logger, app, boot

web_app = FastAPI(title="Music Galaxy Dashboard", version="5.0.0")
templates = Jinja2Templates(directory="devverse/core/templates")
web_app.add_middleware(SessionMiddleware, secret_key=config.API_HASH or "MusicGalaxy_secret_key")


def is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated", False)


def auth_required(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=303, headers={"Location": "/"})


# ═══════════════════════════════════════════════════════════════════
# ─── MAIN DASHBOARD ─────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not is_authenticated(request):
        return templates.TemplateResponse(request, "login.html")

    users_count       = len(await db.get_users())
    chats_count       = len(await db.get_chats())
    sudoers_count     = len(await db.get_sudoers())
    gbans_count       = len(await db.get_gbans())
    calls_count       = len(db.active_calls)
    total_songs       = await db.get_total_songs_played()
    restricted_count  = len(await db.get_restricted_users())

    cpu_usage  = psutil.cpu_percent()
    ram        = psutil.virtual_memory()
    try:
        disk = psutil.disk_usage("/")
    except Exception:
        class DummyDisk:
            percent = 0
            used = 0
            total = 100 * 1024**3
        disk = DummyDisk()
    
    uptime_sec = int(time.time() - boot)
    uptime_str = f"{uptime_sec // 86400}d {(uptime_sec % 86400) // 3600}h {(uptime_sec % 3600) // 60}m"

    stats = {
        "users": users_count,
        "chats": chats_count,
        "sudoers": sudoers_count,
        "gbans": gbans_count,
        "calls": calls_count,
        "songs": total_songs,
        "restricted": restricted_count,
    }

    system = {
        "cpu": cpu_usage,
        "ram": ram.percent,
        "ram_used": f"{ram.used / 1024**3:.1f}",
        "ram_total": f"{ram.total / 1024**3:.1f}",
        "disk": disk.percent,
        "disk_used": f"{disk.used / 1024**3:.1f}",
        "disk_total": f"{disk.total / 1024**3:.1f}",
        "uptime": uptime_str,
        "auto_leave": config.AUTO_LEAVE,
        "auto_end": config.AUTO_END,
        "maintenance": config.MAINTENANCE,
        "pid": os.getpid(),
    }

    active_vcs = []
    for chat_id, status in db.active_calls.items():
        try:
            chat = await app.get_chat(chat_id)
            active_vcs.append({
                "id": chat_id,
                "title": chat.title or "Unknown",
                "username": chat.username or "",
                "members": getattr(chat, "members_count", 0),
                "playing": bool(status)
            })
        except Exception:
            active_vcs.append({"id": chat_id, "title": "Encrypted Chat", "username": "", "members": 0, "playing": bool(status)})

    # Audit logs with extra info
    formatted_logs = []
    for log in await db.get_audit_logs(100):
        u_id = log["user_id"]
        c_id = log["chat_id"]
        performer = "OWNER" if u_id == config.OWNER_ID else (f"User:{u_id}" if u_id else "DASHBOARD")
        target = f"Chat:{c_id}" if c_id else "SYSTEM"
        formatted_logs.append({
            "id": log["id"],
            "timestamp": datetime.fromtimestamp(log["timestamp"]).strftime("%d/%m %H:%M:%S"),
            "action": log["action"],
            "performer": performer,
            "target": target,
            "extra": log["extra_info"] or "",
        })

    # Song request logs
    song_logs = await db.get_song_requests(50)
    for s in song_logs:
        s["requested_at"] = datetime.fromtimestamp(s["requested_at"]).strftime("%d/%m %H:%M")

    # All users/groups info
    all_users_info  = await db.get_all_users_info(200)
    all_groups_info = await db.get_all_groups_info(200)
    all_spies       = await db.get_all_spies()

    # Assistants info
    from devverse import userbot as ub_module
    assistants = []
    for i, client in enumerate(ub_module.clients):
        try:
            me = await client.get_me()
            assistants.append({
                "index": i + 1,
                "id": me.id,
                "name": me.first_name,
                "username": me.username or "N/A",
                "active_chats": sum(1 for cid, num in db.assistant.items() if num == i + 1 and cid in db.active_calls),
            })
        except Exception:
            assistants.append({"index": i + 1, "id": 0, "name": "Offline", "username": "N/A", "active_chats": 0})

    restricted_users = await db.get_restricted_users()
    searched_group = request.session.pop("searched_group", None)
    last_link = request.session.pop("last_link", None)

    # Premium chats + file registry + admin alerts
    premium_chats   = await db.get_premium_chats()
    file_registry   = await db.get_file_registry(50)
    admin_alerts    = await db.get_admin_alerts(50)


    # Format admin alerts timestamps
    for a in admin_alerts:
        try:
            a["alerted_at_str"] = datetime.fromtimestamp(a["alerted_at"]).strftime("%d/%m %H:%M")
        except Exception:
            a["alerted_at_str"] = "N/A"

    # Format file registry timestamps
    for f in file_registry:
        try:
            f["uploaded_at_str"] = datetime.fromtimestamp(f["uploaded_at"]).strftime("%d/%m %H:%M")
            f["expires_in"] = max(0, int(f["expires_at"] - time.time()))
        except Exception:
            f["uploaded_at_str"] = "N/A"
            f["expires_in"] = 0

    return templates.TemplateResponse(request, "dashboard.html", {
        "stats": stats,
        "system": system,
        "sudo_users": await db.get_sudoers(),
        "all_users": await db.get_users(),
        "all_chats": await db.get_chats(),
        "active_vcs": active_vcs,
        "audit_logs": formatted_logs,
        "song_logs": song_logs,
        "spy_users": list(app.spy_users),
        "all_spies": all_spies,
        "all_users_info": all_users_info,
        "all_groups_info": all_groups_info,
        "assistants": assistants,
        "restricted_users": restricted_users,
        "searched_group": searched_group,
        "last_link": last_link,
        "bot_name": app.name if hasattr(app, 'name') else "Music Galaxy",
        "owner_id": config.OWNER_ID,
        "gbans": await db.get_gbans(),
        "premium_chats": premium_chats,
        "file_registry": file_registry,
        "admin_alerts": admin_alerts,

        "current_api": await db.get_api(),
    })


# ═══════════════════════════════════════════════════════════════════
# ─── AUTH ────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/login")
async def login(request: Request, password: str = Form(...)):
    expected = await db.get_web_password()
    logger.info(f"Login attempt. Received: '{password}' | Expected: '{expected}'")
    if password.strip() == expected.strip():
        request.session["authenticated"] = True
        await db.add_audit_log("Dashboard Login", extra_info=f"IP: {request.client.host}")
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url="/?error=1", status_code=303)

@web_app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


# ═══════════════════════════════════════════════════════════════════
# ─── STREAM CONTROLS ─────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/stop-stream")
async def stop_stream(request: Request, chat_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    from devverse import anon
    await anon.stop(chat_id)
    await db.add_audit_log("Stopped Stream", chat_id=chat_id, extra_info="Via Dashboard")
    return RedirectResponse(url="/?tab=overview&success=Stream+stopped", status_code=303)

@web_app.post("/skip-stream")
async def skip_stream(request: Request, chat_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    from devverse import anon
    await anon.play_next(chat_id)
    await db.add_audit_log("Skipped Stream", chat_id=chat_id)
    return RedirectResponse(url="/?tab=overview&success=Track+skipped", status_code=303)

@web_app.post("/pause-stream")
async def pause_stream(request: Request, chat_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    from devverse import anon
    await anon.pause(chat_id)
    await db.add_audit_log("Paused Stream", chat_id=chat_id)
    return RedirectResponse(url="/?tab=overview", status_code=303)

@web_app.post("/resume-stream")
async def resume_stream(request: Request, chat_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    from devverse import anon
    await anon.resume(chat_id)
    await db.add_audit_log("Resumed Stream", chat_id=chat_id)
    return RedirectResponse(url="/?tab=overview", status_code=303)


# ═══════════════════════════════════════════════════════════════════
# ─── GBAN / UNGBAN ───────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/gban")
async def gban(request: Request, user_id: int = Form(...), reason: str = Form(default="Banned via Dashboard")):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.add_gban(user_id, reason)
    app.bl_users.add(user_id)
    await db.add_audit_log(f"GBAN: {user_id}", extra_info=reason)
    return RedirectResponse(url="/?tab=remote&success=User+globally+banned", status_code=303)

@web_app.post("/ungban")
async def ungban(request: Request, user_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.del_gban(user_id)
    app.bl_users.discard(user_id)
    await db.add_audit_log(f"UNGBAN: {user_id}")
    return RedirectResponse(url="/?tab=remote&success=User+unbanned", status_code=303)


# ═══════════════════════════════════════════════════════════════════
# ─── REMOTE ADMIN CONSOLE ────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/remote-admin")
async def remote_admin(
    request: Request,
    user_id: str = Form(...),
    chat_id: int = Form(...),
    action: str = Form(...)
):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)

    try:
        try:
            target_user = int(user_id)
        except ValueError:
            user = await app.get_users(user_id)
            target_user = user.id

        if action == "ban":
            await app.ban_chat_member(chat_id, target_user)
        elif action == "kick":
            await app.ban_chat_member(chat_id, target_user)
            await app.unban_chat_member(chat_id, target_user)
        elif action == "mute":
            await app.restrict_chat_member(chat_id, target_user, ChatPermissions())
        elif action == "unmute":
            await app.restrict_chat_member(chat_id, target_user, ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True
            ))
        elif action == "unban":
            await app.unban_chat_member(chat_id, target_user)
        elif action == "promote":
            await app.promote_chat_member(chat_id, target_user, privileges=ChatPrivileges(
                can_manage_chat=True, can_delete_messages=True,
                can_manage_video_chats=True, can_restrict_members=True,
                can_promote_members=False, can_change_info=True,
                can_invite_users=True, can_pin_messages=True,
            ))
        elif action == "demote":
            await app.promote_chat_member(chat_id, target_user, privileges=ChatPrivileges())
        elif action == "admin_title":
            await app.set_administrator_title(chat_id, target_user, "Bot Admin")
        elif action == "restrict_bot":
            await db.restrict_user(target_user, "Restricted via Dashboard")
        elif action == "unrestrict_bot":
            await db.unrestrict_user(target_user)

        await db.add_audit_log(f"Remote {action.upper()}: {target_user}", chat_id=chat_id)
        return RedirectResponse(url=f"/?tab=remote&success={action}+executed", status_code=303)

    except Exception as e:
        logger.error(f"Remote admin error: {e}")
        return RedirectResponse(url=f"/?tab=remote&error={str(e)[:100]}", status_code=303)


# ═══════════════════════════════════════════════════════════════════
# ─── GROUP MANAGER ───────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/group-search")
async def group_search(request: Request, chat_id: str = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    try:
        cid = int(chat_id)
        chat = await app.get_chat(cid)
        info = {
            "id": chat.id,
            "title": chat.title or "N/A",
            "username": f"@{chat.username}" if chat.username else "Private",
            "type": str(chat.type).replace("ChatType.", ""),
            "members": getattr(chat, "members_count", 0),
            "description": chat.description or "No description",
            "invite_link": getattr(chat, "invite_link", "N/A") or "N/A",
            "is_restricted": getattr(chat, "is_restricted", False),
            "is_verified": getattr(chat, "is_verified", False),
            "dc_id": getattr(chat, "dc_id", "N/A"),
        }
        # Store/update group info
        await db.update_group_info(
            cid, title=chat.title, username=chat.username,
            member_count=getattr(chat, "members_count", 0),
            description=chat.description
        )
        request.session["searched_group"] = info
        return RedirectResponse(url="/?tab=groups&group_found=1", status_code=303)
    except Exception as e:
        logger.error(f"Group search error: {e}")
        return RedirectResponse(url=f"/?tab=groups&error={str(e)[:100]}", status_code=303)

@web_app.get("/group-info")
async def group_info_api(request: Request, chat_id: int):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        chat = await app.get_chat(chat_id)
        return JSONResponse({
            "id": chat.id,
            "title": chat.title or "N/A",
            "username": chat.username or "",
            "type": str(chat.type).replace("ChatType.", ""),
            "members": getattr(chat, "members_count", 0),
            "description": chat.description or "",
            "invite_link": getattr(chat, "invite_link", "") or "",
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@web_app.post("/group-action")
async def group_action(
    request: Request,
    chat_id: int = Form(...),
    action: str = Form(...),
    extra: str = Form(default="")
):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    try:
        if action == "set_title":
            await app.set_chat_title(chat_id, extra)
        elif action == "set_description":
            await app.set_chat_description(chat_id, extra)
        elif action == "get_link":
            link = await app.export_chat_invite_link(chat_id)
            request.session["last_link"] = link
        elif action == "revoke_link":
            link = await app.export_chat_invite_link(chat_id)
            request.session["last_link"] = link
        elif action == "leave_bot":
            await app.leave_chat(chat_id)
            await db.rm_chat(chat_id)
        elif action == "lock_group":
            await app.set_chat_permissions(chat_id, ChatPermissions())
        elif action == "unlock_group":
            await app.set_chat_permissions(chat_id, ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_invite_users=True,
            ))
        elif action == "delete_all_messages":
            async for msg in app.get_chat_history(chat_id, limit=200):
                try:
                    await msg.delete()
                except Exception:
                    pass
        elif action == "kick_all":
            async for member in app.get_chat_members(chat_id):
                try:
                    if not member.status.value in ["administrator", "creator", "owner"]:
                        await app.ban_chat_member(chat_id, member.user.id)
                        await app.unban_chat_member(chat_id, member.user.id)
                except Exception:
                    pass
        elif action == "ban_all":
            async for member in app.get_chat_members(chat_id):
                try:
                    if not member.status.value in ["administrator", "creator", "owner"]:
                        await app.ban_chat_member(chat_id, member.user.id)
                except Exception:
                    pass
        elif action == "mute_all":
            await app.set_chat_permissions(chat_id, ChatPermissions(
                can_send_messages=False,
            ))
        elif action == "unmute_all":
            await app.set_chat_permissions(chat_id, ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
            ))
        elif action == "start_vc":
            client = await db.get_assistant(chat_id)
            from pytgcalls.types import MediaStream
            await client.play(chat_id, MediaStream("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"))
        elif action == "close_vc":
            from devverse import anon
            await anon.stop(chat_id)
        elif action == "delete_user_messages":
            target_id = int(extra) if extra.isdigit() else 0
            if target_id:
                async for msg in app.get_chat_history(chat_id, limit=500):
                    try:
                        if msg.from_user and msg.from_user.id == target_id:
                            await msg.delete()
                    except Exception:
                        pass

        await db.add_audit_log(f"Group {action.upper()}", chat_id=chat_id, extra_info=extra or None)
        return RedirectResponse(url=f"/?tab=groups&success={action}+done", status_code=303)
    except Exception as e:
        logger.error(f"Group action error: {e}")
        return RedirectResponse(url=f"/?tab=groups&error={str(e)[:150]}", status_code=303)


# ═══════════════════════════════════════════════════════════════════
# ─── ASSISTANT CONTROLS ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/assistant-action")
async def assistant_action(
    request: Request,
    assistant_index: int = Form(...),
    chat_id: int = Form(default=0),
    action: str = Form(...)
):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    from devverse import userbot as ub_module
    try:
        idx = assistant_index - 1
        if idx < 0 or idx >= len(ub_module.clients):
            return RedirectResponse(url="/?tab=assistants&error=Invalid+assistant+index", status_code=303)
        client = ub_module.clients[idx]

        if action == "leave_vc":
            if chat_id:
                from devverse import anon
                await anon.stop(chat_id)
        elif action == "leave_group":
            if chat_id:
                await client.leave_chat(chat_id)
        elif action == "leave_all_groups":
            async for dialog in client.get_dialogs():
                if dialog.chat.type in ["group", "supergroup"]:
                    try:
                        await client.leave_chat(dialog.chat.id)
                        await asyncio.sleep(1)
                    except Exception:
                        pass
        elif action == "leave_all_vcs":
            for cid in list(db.active_calls.keys()):
                try:
                    from devverse import anon
                    await anon.stop(cid)
                except Exception:
                    pass

        await db.add_audit_log(f"Assistant #{assistant_index} {action.upper()}", chat_id=chat_id)
        return RedirectResponse(url="/?tab=assistants&success=Done", status_code=303)
    except Exception as e:
        logger.error(f"Assistant action error: {e}")
        return RedirectResponse(url=f"/?tab=assistants&error={str(e)[:100]}", status_code=303)


# ═══════════════════════════════════════════════════════════════════
# ─── ADVANCED BROADCAST ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/broadcast")
async def broadcast(
    request: Request,
    message: str = Form(default=""),
    media_link: str = Form(default=""),
    target_type: str = Form(default="all"),  # all | specific_uid | specific_group
    target_id: str = Form(default=""),
    pin_message: str = Form(default="0"),
):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)

    logger.info(f"Broadcast started: type={target_type} target={target_id}")
    await db.add_audit_log(f"BROADCAST: {target_type}", extra_info=f"msg={message[:50]}")
    asyncio.create_task(send_broadcast(message, media_link, target_type, target_id, pin_message == "1"))
    return RedirectResponse(url="/?tab=overview&success=Broadcast+initiated", status_code=303)


async def send_broadcast(message: str, media_link: str, target_type: str,
                          target_id: str, pin: bool = False):
    targets = []
    if target_type == "all":
        targets = await db.get_chats()
    elif target_type == "all_users":
        targets = await db.get_users()
    elif target_type == "specific_group":
        try:
            targets = [int(t.strip()) for t in target_id.split(",") if t.strip()]
        except ValueError:
            logger.error("Invalid target group IDs for broadcast")
            return
    elif target_type == "specific_uid":
        try:
            targets = [int(t.strip()) for t in target_id.split(",") if t.strip()]
        except ValueError:
            logger.error("Invalid target user IDs for broadcast")
            return

    sent = failed = 0
    for target in targets:
        try:
            sent_msg = None
            if media_link and media_link.startswith("http"):
                # Send as photo/video with caption
                try:
                    sent_msg = await app.send_photo(target, media_link, caption=message)
                except Exception:
                    sent_msg = await app.send_message(target, message)
            elif message:
                sent_msg = await app.send_message(target, message)

            if sent_msg and pin:
                try:
                    await sent_msg.pin(disable_notification=True)
                except Exception:
                    pass

            sent += 1
            await asyncio.sleep(0.35)
        except Exception as e:
            failed += 1
            logger.debug(f"Broadcast failed to {target}: {e}")

    logger.info(f"Broadcast complete: {sent} sent, {failed} failed")
    # Notify logger
    try:
        await app.send_message(config.LOGGER_ID,
            f"✅ <b>Broadcast Complete</b>\n"
            f"📨 Sent: <code>{sent}</code>\n"
            f"❌ Failed: <code>{failed}</code>\n"
            f"🎯 Type: <code>{target_type}</code>"
        )
    except Exception:
        pass


@web_app.get("/download-users-txt", response_class=PlainTextResponse)
async def download_users_txt(request: Request):
    if not is_authenticated(request): return PlainTextResponse("Unauthorized", status_code=401)
    users = await db.get_users()
    return PlainTextResponse("\n".join(map(str, users)), headers={"Content-Disposition": "attachment; filename=users.txt"})

@web_app.get("/download-groups-txt", response_class=PlainTextResponse)
async def download_groups_txt(request: Request):
    if not is_authenticated(request): return PlainTextResponse("Unauthorized", status_code=401)
    chats = await db.get_chats()
    return PlainTextResponse("\n".join(map(str, chats)), headers={"Content-Disposition": "attachment; filename=groups.txt"})

# ═══════════════════════════════════════════════════════════════════
# ─── SPY SYSTEM ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/add-spy")
async def add_spy(
    request: Request,
    user_id: int = Form(...),
    dest_group_id: int = Form(default=0)
):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    app.spy_users.add(user_id)
    await db.add_spy(user_id, dest_group_id)
    await db.add_audit_log(f"Spy Added: {user_id}", extra_info=f"Dest: {dest_group_id or 'LOGGER'}")
    return RedirectResponse(url="/?tab=remote&success=Spy+activated", status_code=303)

@web_app.post("/remove-spy")
async def remove_spy(request: Request, user_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    app.spy_users.discard(user_id)
    await db.del_spy(user_id)
    await db.add_audit_log(f"Spy Removed: {user_id}")
    return RedirectResponse(url="/?tab=remote&success=Spy+deactivated", status_code=303)


# ═══════════════════════════════════════════════════════════════════
# ─── SUDO & USER MANAGEMENT ──────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/add-sudo")
async def add_sudo(request: Request, user_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.add_sudo(user_id)
    app.sudoers.add(user_id)
    await db.add_audit_log(f"Sudo Granted: {user_id}")
    return RedirectResponse(url="/?tab=remote&success=Sudo+granted", status_code=303)

@web_app.post("/del-sudo")
async def del_sudo(request: Request, user_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.del_sudo(user_id)
    app.sudoers.discard(user_id)
    await db.add_audit_log(f"Sudo Revoked: {user_id}")
    return RedirectResponse(url="/?tab=remote&success=Sudo+revoked", status_code=303)

@web_app.post("/restrict-user")
async def restrict_user_endpoint(request: Request, user_id: int = Form(...), reason: str = Form(default="Restricted via Dashboard")):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.restrict_user(user_id, reason)
    await db.add_audit_log(f"User Restricted: {user_id}", extra_info=reason)
    return RedirectResponse(url="/?tab=users&success=User+restricted", status_code=303)

@web_app.post("/unrestrict-user")
async def unrestrict_user_endpoint(request: Request, user_id: int = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.unrestrict_user(user_id)
    await db.add_audit_log(f"User Unrestricted: {user_id}")
    return RedirectResponse(url="/?tab=users&success=User+unrestricted", status_code=303)


# ═══════════════════════════════════════════════════════════════════
# ─── SYSTEM CONTROLS ─────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/toggle")
async def toggle_conf(request: Request, key: str = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    if key == "auto_leave":
        config.AUTO_LEAVE = not config.AUTO_LEAVE
    elif key == "auto_end":
        config.AUTO_END = not config.AUTO_END
    elif key == "maintenance":
        config.MAINTENANCE = not config.MAINTENANCE
    await db.add_audit_log(f"Toggled: {key}")
    return RedirectResponse(url="/?tab=overview", status_code=303)

@web_app.post("/addapi")
async def add_api(request: Request, api_url: str = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.set_api(api_url)
    await db.add_audit_log("Set Download API", extra_info=api_url)
    return RedirectResponse(url="/?success=API+updated", status_code=303)

@web_app.post("/update-password")
async def update_password(request: Request, new_password: str = Form(...)):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.set_web_password(new_password)
    await db.add_audit_log("Updated Admin Password")
    return RedirectResponse(url="/?success=Password+updated", status_code=303)

@web_app.post("/clean")
async def clean_cache(request: Request):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    import shutil
    cleaned = []
    for folder in ["downloads", "cache"]:
        if os.path.exists(folder):
            size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fns in os.walk(folder) for f in fns)
            shutil.rmtree(folder)
            os.makedirs(folder)
            cleaned.append(f"{folder} ({size // 1024}KB)")
    await db.add_audit_log(f"Cache Cleaned: {', '.join(cleaned)}")
    logger.info(f"Cache cleaned: {cleaned}")
    return RedirectResponse(url="/?tab=overview&success=Cache+cleaned", status_code=303)

@web_app.post("/clear-logs")
async def clear_audits(request: Request):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.clear_audit_logs()
    return RedirectResponse(url="/?tab=logs&success=Audit+logs+cleared", status_code=303)

@web_app.post("/clear-song-logs")
async def clear_song_logs(request: Request):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.clear_song_requests()
    await db.add_audit_log("Song Logs Cleared via Dashboard")
    return RedirectResponse(url="/?tab=songlogs&success=Song+logs+cleared", status_code=303)

@web_app.get("/api/spy-list")
async def api_spy_list(request: Request):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    spies = await db.get_all_spies()
    return JSONResponse(spies)

@web_app.get("/api/users-info")
async def api_users_info(request: Request):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    users = await db.get_all_users_info(500)
    return JSONResponse(users)

@web_app.get("/api/now-playing")
async def api_now_playing(request: Request):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from devverse import queue as q
    results = []
    for chat_id, status in db.active_calls.items():
        cur = q.get_current(chat_id)
        if not cur:
            continue
        try:
            chat = await app.get_chat(chat_id)
            title = chat.title or "Unknown"
        except Exception:
            title = "Encrypted"
        progress = 0
        if cur.duration_sec > 0 and cur.time > 0:
            progress = min(100, int(cur.time / cur.duration_sec * 100))
        results.append({
            "chat_id": chat_id,
            "chat_title": title,
            "title": cur.title or "Unknown",
            "url": cur.url or "",
            "duration": cur.duration or "00:00",
            "duration_sec": cur.duration_sec,
            "elapsed": cur.time,
            "progress": progress,
            "requester": cur.user or "Unknown",
            "paused": not bool(status or 0),
            "video": cur.video,
        })
    return JSONResponse(results)

@web_app.get("/api/queue/{chat_id}")
async def api_queue(request: Request, chat_id: int):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from devverse import queue as q
    items = q.get_queue(chat_id)
    queue_list = []
    for i, item in enumerate(items):
        queue_list.append({
            "index": i,
            "title": item.title or "Unknown",
            "url": item.url or "",
            "duration": item.duration or "00:00",
            "requester": item.user or "Unknown",
        })
    return JSONResponse({"queue": queue_list, "count": len(queue_list)})

@web_app.post("/api/remove-queue")
async def api_remove_queue(request: Request, chat_id: int = Form(...), index: int = Form(...)):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from devverse import queue as q
    items = q.get_queue(chat_id)
    if 0 <= index < len(items):
        items.pop(index)
        # Rebuild deque
        from collections import deque
        q.queues[chat_id] = deque(items)
        await db.add_audit_log(f"Queue item {index} removed for {chat_id}")
        return JSONResponse({"success": True})
    return JSONResponse({"error": "Invalid index"}, status_code=400)

@web_app.post("/restart")
async def restart(request: Request):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.add_audit_log("System Restart via Dashboard")
    logger.info("Restart triggered from Dashboard")
    asyncio.create_task(_delayed_restart())
    return RedirectResponse(url="/?success=Restarting", status_code=303)

async def _delayed_restart():
    await asyncio.sleep(1)
    os._exit(0)


# ═══════════════════════════════════════════════════════════════════
# ─── LOG & DB ENDPOINTS ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.get("/logs", response_class=PlainTextResponse)
async def get_logs(request: Request):
    if not is_authenticated(request): return "Unauthorized"
    if os.path.exists("log.txt"):
        with open("log.txt", "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-200:])
    return "Log file not found."

@web_app.get("/download-db")
async def download_db(request: Request):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    if os.path.exists("database.db"):
        await db.add_audit_log("DB Downloaded via Dashboard")
        return FileResponse("database.db", media_type="application/x-sqlite3", filename="Delete_ee_backup.db")
    return JSONResponse({"error": "Database not found"}, status_code=404)

@web_app.get("/api/stats")
async def api_stats(request: Request):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return JSONResponse({
        "users": len(await db.get_users()),
        "chats": len(await db.get_chats()),
        "active_calls": len(db.active_calls),
        "songs_played": await db.get_total_songs_played(),
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
    })


# ═══════════════════════════════════════════════════════════════════
# ─── SERVER STARTER ──────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# ─── PREMIUM MANAGEMENT ────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@web_app.post("/set-premium")
async def set_premium(
    request: Request,
    chat_id: int = Form(...),
    plan: str = Form(default="pro"),
    days: int = Form(default=30)
):
    if not is_authenticated(request): return RedirectResponse(url="/", status_code=303)
    await db.set_premium(chat_id, granted_by=config.OWNER_ID, plan=plan, days=days)
    await db.add_audit_log(f"Premium Set: {chat_id} ({plan} {days}d)")
    return RedirectResponse(url="/?tab=premium&success=Premium+activated", status_code=303)


# ═══════════════════════════════════════════════════════════════════

@web_app.get("/api/file-registry")
async def api_file_registry(request: Request):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    files = await db.get_file_registry(100)
    return JSONResponse(files)

@web_app.get("/api/admin-alerts")
async def api_admin_alerts(request: Request):
    if not is_authenticated(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    alerts = await db.get_admin_alerts(100)
    return JSONResponse(alerts)


# ═══════════════════════════════════════════════════════════════════
# ─── SERVER STARTER ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def start_web():
    logger.info("Starting Web Dashboard on port %d", config.PORT)
    cfg = uvicorn.Config(web_app, host="0.0.0.0", port=config.PORT, log_level="error")
    server = uvicorn.Server(cfg)
    await server.serve()

