# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee — by @Delete_ee
#
# Optional MongoDB backend. Enabled when DATABASE_MONGO=true.
# Mirrors the public API of the SQLite Database class.

import motor.motor_asyncio
from pymongo import ReturnDocument
from random import randint
from time import time
from typing import List, Set, Union, Optional, Dict

from devverse import config, logger, userbot


class MongoDatabase:
    def __init__(self, uri: str = None):
        self.uri = uri or config.MONGO_URI
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db = None

        # Caches (identical semantics to the SQLite backend)
        self.admin_list = {}
        self.active_calls = {}
        self.admin_play = []
        self.blacklisted = []
        self.cmd_delete = []
        self.loop = {}
        self.notified = []
        self.logger_status = False
        self.assistant = {}
        self.auth = {}
        self.chats = []
        self.users = []
        self.sudoers = []
        self.lang = {}

    # ─── CONNECTION ──────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Initialize the MongoDB connection and create indexes."""
        try:
            start = time()
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                self.uri, serverSelectionTimeoutMS=5000
            )
            db_name = "music_galaxy"
            try:
                from urllib.parse import urlparse
                path = urlparse(self.uri).path.strip("/")
                if path:
                    db_name = path
            except Exception:
                pass
            self.db = self.client[db_name]
            await self._create_indexes()
            logger.info(f"MongoDB connection successful. ({time() - start:.2f}s)")
            await self.load_cache()
        except Exception as e:
            logger.exception("MongoDB connection failed")
            raise SystemExit(f"MongoDB connection failed: {type(e).__name__}: {e}") from e

    async def _create_indexes(self) -> None:
        await self.db.auth.create_index("chat_id")
        await self.db.auth.create_index("user_id")
        await self.db.song_requests.create_index("user_id")
        await self.db.song_requests.create_index("chat_id")

    async def _next_id(self, name: str) -> int:
        """Atomically generate an auto-increment id for a collection."""
        doc = await self.db.counters.find_one_and_update(
            {"_id": name}, {"$inc": {"seq": 1}},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
        return doc["seq"]

    async def close(self) -> None:
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    # Raw-SQL helpers are not used by the MongoDB backend; kept for interface
    # parity but raise if someone calls them directly.
    async def execute(self, query: str, *args):
        raise NotImplementedError(
            "execute() is only available on the SQLite backend"
        )

    async def fetchall(self, query: str, *args):
        raise NotImplementedError(
            "fetchall() is only available on the SQLite backend"
        )

    async def fetchone(self, query: str, *args):
        raise NotImplementedError(
            "fetchone() is only available on the SQLite backend"
        )

    # ─── CACHE METHODS ────────────────────────────────────────────────────────

    async def get_call(self, chat_id: int) -> bool:
        return chat_id in self.active_calls

    async def add_call(self, chat_id: int) -> None:
        self.active_calls[chat_id] = 1

    async def remove_call(self, chat_id: int) -> None:
        self.active_calls.pop(chat_id, None)

    async def playing(self, chat_id: int, paused: bool = None) -> Union[bool, None]:
        if paused is not None:
            self.active_calls[chat_id] = int(not paused)
        return bool(self.active_calls.get(chat_id, 0))

    async def get_admins(self, chat_id: int, reload: bool = False) -> List[int]:
        from devverse.helpers._admins import reload_admins
        if chat_id not in self.admin_list or reload:
            self.admin_list[chat_id] = await reload_admins(chat_id)
        return self.admin_list[chat_id]

    async def get_loop(self, chat_id: int) -> int:
        return self.loop.get(chat_id, 0)

    async def set_loop(self, chat_id: int, count: int) -> None:
        self.loop[chat_id] = count

    async def notify_user(self, user_id: int) -> None:
        """Mark a blacklisted user as notified so they only see the notification once."""
        if user_id not in self.notified:
            self.notified.append(user_id)

    # ─── AUTH METHODS ─────────────────────────────────────────────────────────

    async def _get_auth(self, chat_id: int) -> Set[int]:
        if chat_id not in self.auth:
            cursor = self.db.auth.find({"chat_id": chat_id}, {"user_id": 1})
            self.auth[chat_id] = {doc["user_id"] async for doc in cursor}
        return self.auth[chat_id]

    async def is_auth(self, chat_id: int, user_id: int) -> bool:
        return user_id in await self._get_auth(chat_id)

    async def add_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id not in users:
            users.add(user_id)
            await self.db.auth.replace_one(
                {"chat_id": chat_id, "user_id": user_id},
                {"chat_id": chat_id, "user_id": user_id},
                upsert=True,
            )

    async def rm_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id in users:
            users.discard(user_id)
            await self.db.auth.delete_one({"chat_id": chat_id, "user_id": user_id})

    # ─── ASSISTANT METHODS ────────────────────────────────────────────────────

    async def set_assistant(self, chat_id: int) -> int:
        if not userbot.clients:
            num = 1
        else:
            num = randint(1, len(userbot.clients))
        await self.db.assistant.replace_one(
            {"_id": chat_id}, {"_id": chat_id, "num": num}, upsert=True
        )
        self.assistant[chat_id] = num
        return num

    async def get_assistant(self, chat_id: int):
        from devverse import anon
        if chat_id not in self.assistant:
            doc = await self.db.assistant.find_one({"_id": chat_id})
            num = doc["num"] if doc else await self.set_assistant(chat_id)
            self.assistant[chat_id] = num
        try:
            return anon.clients[self.assistant[chat_id] - 1]
        except IndexError:
            if userbot.clients:
                num = randint(1, len(userbot.clients))
                self.assistant[chat_id] = num
                return anon.clients[num - 1]
            raise

    async def get_client(self, chat_id: int):
        if chat_id not in self.assistant:
            await self.get_assistant(chat_id)
        client_map = {i + 1: client for i, client in enumerate(userbot.clients)}
        return client_map.get(self.assistant[chat_id])

    # ─── BLACKLIST METHODS ────────────────────────────────────────────────────

    async def add_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            if chat_id not in self.blacklisted:
                self.blacklisted.append(chat_id)
                await self.db.blacklist_chats.replace_one(
                    {"_id": chat_id}, {"_id": chat_id}, upsert=True
                )
        else:
            await self.db.blacklist_users.replace_one(
                {"_id": chat_id}, {"_id": chat_id}, upsert=True
            )

    async def del_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            if chat_id in self.blacklisted:
                self.blacklisted.remove(chat_id)
                await self.db.blacklist_chats.delete_one({"_id": chat_id})
        else:
            await self.db.blacklist_users.delete_one({"_id": chat_id})

    async def get_blacklisted(self, chat: bool = False) -> List[int]:
        if chat:
            if not self.blacklisted:
                cursor = self.db.blacklist_chats.find({}, {"_id": 1})
                self.blacklisted = [doc["_id"] async for doc in cursor]
            return self.blacklisted
        cursor = self.db.blacklist_users.find({}, {"_id": 1})
        return [doc["_id"] async for doc in cursor]

    # ─── CHAT METHODS ─────────────────────────────────────────────────────────

    async def is_chat(self, chat_id: int) -> bool:
        return chat_id in self.chats

    async def add_chat(self, chat_id: int) -> None:
        if not await self.is_chat(chat_id):
            self.chats.append(chat_id)
            await self.db.chats.replace_one({"_id": chat_id}, {"_id": chat_id}, upsert=True)

    async def rm_chat(self, chat_id: int) -> None:
        if await self.is_chat(chat_id):
            self.chats.remove(chat_id)
            await self.db.chats.delete_one({"_id": chat_id})

    async def get_chats(self) -> List[int]:
        if not self.chats:
            cursor = self.db.chats.find({}, {"_id": 1})
            self.chats = [doc["_id"] async for doc in cursor]
        return self.chats

    # ─── COMMAND DELETE ───────────────────────────────────────────────────────

    async def get_cmd_delete(self, chat_id: int) -> bool:
        if chat_id not in self.cmd_delete:
            doc = await self.db.chats.find_one({"_id": chat_id}, {"cmd_delete": 1})
            if doc and doc.get("cmd_delete"):
                self.cmd_delete.append(chat_id)
        return chat_id in self.cmd_delete

    async def set_cmd_delete(self, chat_id: int, delete: bool = False) -> None:
        if delete:
            if chat_id not in self.cmd_delete:
                self.cmd_delete.append(chat_id)
        else:
            if chat_id in self.cmd_delete:
                self.cmd_delete.remove(chat_id)
        await self.db.chats.replace_one(
            {"_id": chat_id},
            {"_id": chat_id, "cmd_delete": int(delete)},
            upsert=True,
        )

    # ─── LANGUAGE METHODS ─────────────────────────────────────────────────────

    async def set_lang(self, chat_id: int, lang_code: str):
        await self.db.lang.replace_one(
            {"_id": chat_id}, {"_id": chat_id, "lang": lang_code}, upsert=True
        )
        self.lang[chat_id] = lang_code

    async def get_lang(self, chat_id: int) -> str:
        if chat_id not in self.lang:
            doc = await self.db.lang.find_one({"_id": chat_id}, {"lang": 1})
            self.lang[chat_id] = doc["lang"] if doc else config.LANG_CODE
        return self.lang.get(chat_id, config.LANG_CODE)

    # ─── LOGGER METHODS ───────────────────────────────────────────────────────

    async def is_logger(self) -> bool:
        return self.logger_status

    async def get_logger(self) -> bool:
        doc = await self.db.metadata.find_one({"_id": "logger"})
        if doc:
            self.logger_status = doc.get("value") == "True"
        return self.logger_status

    async def set_logger(self, status: bool) -> None:
        self.logger_status = status
        await self.db.metadata.replace_one(
            {"_id": "logger"}, {"_id": "logger", "value": str(status)}, upsert=True
        )

    # ─── PLAY MODE METHODS ────────────────────────────────────────────────────

    async def get_play_mode(self, chat_id: int) -> bool:
        if chat_id not in self.admin_play:
            doc = await self.db.chats.find_one({"_id": chat_id}, {"admin_play": 1})
            if doc and doc.get("admin_play"):
                self.admin_play.append(chat_id)
        return chat_id in self.admin_play

    async def set_play_mode(self, chat_id: int, remove: bool = False) -> None:
        if remove:
            if chat_id in self.admin_play:
                self.admin_play.remove(chat_id)
        else:
            if chat_id not in self.admin_play:
                self.admin_play.append(chat_id)
        await self.db.chats.replace_one(
            {"_id": chat_id},
            {"_id": chat_id, "admin_play": int(not remove)},
            upsert=True,
        )

    # ─── SUDO METHODS ─────────────────────────────────────────────────────────

    async def add_sudo(self, user_id: int) -> None:
        if user_id not in self.sudoers:
            self.sudoers.append(user_id)
            await self.db.sudoers.replace_one({"_id": user_id}, {"_id": user_id}, upsert=True)

    async def del_sudo(self, user_id: int) -> None:
        if user_id in self.sudoers:
            self.sudoers.remove(user_id)
            await self.db.sudoers.delete_one({"_id": user_id})

    async def get_sudoers(self) -> List[int]:
        if not self.sudoers:
            cursor = self.db.sudoers.find({}, {"_id": 1})
            self.sudoers = [doc["_id"] async for doc in cursor]
        return self.sudoers

    # ─── USER METHODS ─────────────────────────────────────────────────────────

    async def is_user(self, user_id: int) -> bool:
        return user_id in self.users

    async def add_user(self, user_id: int) -> None:
        if not await self.is_user(user_id):
            self.users.append(user_id)
            await self.db.users.replace_one({"_id": user_id}, {"_id": user_id}, upsert=True)

    async def rm_user(self, user_id: int) -> None:
        if await self.is_user(user_id):
            self.users.remove(user_id)
            await self.db.users.delete_one({"_id": user_id})

    async def get_users(self) -> List[int]:
        if not self.users:
            cursor = self.db.users.find({}, {"_id": 1})
            self.users = [doc["_id"] async for doc in cursor]
        return self.users

    # ─── GBAN METHODS ─────────────────────────────────────────────────────────

    async def add_gban(self, user_id: int, reason: str = None) -> None:
        await self.db.gbans.replace_one(
            {"_id": user_id}, {"_id": user_id, "reason": reason}, upsert=True
        )

    async def del_gban(self, user_id: int) -> None:
        await self.db.gbans.delete_one({"_id": user_id})

    async def get_gbans(self) -> List[int]:
        cursor = self.db.gbans.find({}, {"_id": 1})
        return [doc["_id"] async for doc in cursor]

    async def get_gban_reason(self, user_id: int) -> Optional[str]:
        doc = await self.db.gbans.find_one({"_id": user_id}, {"reason": 1})
        return doc.get("reason") if doc else None

    # ─── AUDIT LOG METHODS ────────────────────────────────────────────────────

    async def add_audit_log(self, action: str, user_id: int = 0, chat_id: int = 0, extra_info: str = None) -> None:
        await self.db.audit_log.insert_one(
            {
                "_id": await self._next_id("audit_log"),
                "action": action,
                "user_id": user_id,
                "chat_id": chat_id,
                "extra_info": extra_info,
                "timestamp": time(),
            }
        )

    async def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        cursor = self.db.audit_log.find({}, {"_id": 0}).sort("_id", -1).limit(limit)
        return [doc async for doc in cursor]

    async def clear_audit_logs(self) -> None:
        await self.db.audit_log.delete_many({})

    # ─── ADVANCED SPY SYSTEM ─────────────────────────────────────────────────

    async def add_spy(self, user_id: int, dest_group_id: int = 0) -> None:
        await self.db.spies.replace_one(
            {"_id": user_id},
            {"_id": user_id, "dest_group_id": dest_group_id, "added_at": time()},
            upsert=True,
        )

    async def del_spy(self, user_id: int) -> None:
        await self.db.spies.delete_one({"_id": user_id})

    async def get_spies(self) -> List[int]:
        cursor = self.db.spies.find({}, {"_id": 1})
        return [doc["_id"] async for doc in cursor]

    async def get_spy_dest(self, user_id: int) -> int:
        doc = await self.db.spies.find_one({"_id": user_id}, {"dest_group_id": 1})
        return doc.get("dest_group_id", 0) if doc else 0

    async def get_all_spies(self) -> List[Dict]:
        cursor = self.db.spies.find({}, {"_id": 0, "user_id": 1, "dest_group_id": 1, "added_at": 1})
        return [dict(doc) async for doc in cursor]

    # ─── ADVANCED USER INFO ───────────────────────────────────────────────────

    async def update_user_info(self, user_id: int, username: str = None, first_name: str = None,
                               last_name: str = None, is_bot: bool = False) -> None:
        existing = await self.db.users_info.find_one({"_id": user_id})
        now = time()
        if existing:
            await self.db.users_info.update_one(
                {"_id": user_id},
                {"$set": {"username": username, "first_name": first_name,
                          "last_name": last_name, "last_seen": now}},
            )
        else:
            await self.db.users_info.replace_one(
                {"_id": user_id},
                {"_id": user_id, "username": username, "first_name": first_name,
                 "last_name": last_name, "is_bot": int(is_bot),
                 "join_date": now, "last_seen": now,
                 "total_requests": 0, "is_restricted": 0},
                upsert=True,
            )

    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        doc = await self.db.users_info.find_one({"_id": user_id}, {"_id": 0})
        return dict(doc) if doc else None

    async def get_all_users_info(self, limit: int = 200) -> List[Dict]:
        cursor = self.db.users_info.find({}, {"_id": 0}).sort("last_seen", -1).limit(limit)
        return [dict(doc) async for doc in cursor]

    async def increment_user_requests(self, user_id: int) -> None:
        await self.db.users_info.update_one(
            {"_id": user_id},
            {"$inc": {"total_requests": 1}, "$set": {"last_seen": time()}},
        )

    async def restrict_user(self, user_id: int, reason: str = "Manually restricted") -> None:
        await self.db.restricted_users.replace_one(
            {"_id": user_id},
            {"_id": user_id, "reason": reason, "restricted_at": time()},
            upsert=True,
        )
        await self.db.users_info.update_one(
            {"_id": user_id}, {"$set": {"is_restricted": 1}}, upsert=True
        )

    async def unrestrict_user(self, user_id: int) -> None:
        await self.db.restricted_users.delete_one({"_id": user_id})
        await self.db.users_info.update_one(
            {"_id": user_id}, {"$set": {"is_restricted": 0}}
        )

    async def is_restricted(self, user_id: int) -> bool:
        return await self.db.restricted_users.find_one({"_id": user_id}) is not None

    async def get_restricted_users(self) -> List[Dict]:
        cursor = self.db.restricted_users.find({}, {"_id": 0, "user_id": 1, "reason": 1, "restricted_at": 1}).sort("restricted_at", -1)
        return [dict(doc) async for doc in cursor]

    # ─── ADVANCED GROUP INFO ──────────────────────────────────────────────────

    async def update_group_info(self, chat_id: int, title: str = None, username: str = None,
                                member_count: int = 0, description: str = None) -> None:
        existing = await self.db.groups_info.find_one({"_id": chat_id})
        now = time()
        if existing:
            await self.db.groups_info.update_one(
                {"_id": chat_id},
                {"$set": {"title": title, "username": username,
                          "member_count": member_count, "description": description,
                          "last_active": now}},
            )
        else:
            await self.db.groups_info.replace_one(
                {"_id": chat_id},
                {"_id": chat_id, "title": title, "username": username,
                 "member_count": member_count, "description": description,
                 "join_date": now, "last_active": now,
                 "total_songs_played": 0, "is_blacklisted": 0},
                upsert=True,
            )

    async def get_group_info(self, chat_id: int) -> Optional[Dict]:
        doc = await self.db.groups_info.find_one({"_id": chat_id}, {"_id": 0})
        return dict(doc) if doc else None

    async def get_all_groups_info(self, limit: int = 200) -> List[Dict]:
        cursor = self.db.groups_info.find({}, {"_id": 0}).sort("last_active", -1).limit(limit)
        return [dict(doc) async for doc in cursor]

    async def increment_group_songs(self, chat_id: int) -> None:
        await self.db.groups_info.update_one(
            {"_id": chat_id},
            {"$inc": {"total_songs_played": 1}, "$set": {"last_active": time()}},
        )

    # ─── SONG REQUEST LOG ─────────────────────────────────────────────────────

    async def log_song_request(self, user_id: int, username: str, first_name: str,
                               chat_id: int, chat_title: str, song_name: str,
                               song_link: str = None, duration: str = None) -> None:
        await self.db.song_requests.insert_one(
            {
                "_id": await self._next_id("song_requests"),
                "user_id": user_id,
                "username": username or "Unknown",
                "first_name": first_name or "Unknown",
                "chat_id": chat_id,
                "chat_title": chat_title or "Unknown",
                "song_name": song_name,
                "song_link": song_link,
                "duration": duration,
                "requested_at": time(),
            }
        )
        await self.increment_user_requests(user_id)
        await self.increment_group_songs(chat_id)

    async def get_song_requests(self, limit: int = 100) -> List[Dict]:
        cursor = self.db.song_requests.find({}, {"_id": 0}).sort("_id", -1).limit(limit)
        return [dict(doc) async for doc in cursor]

    async def get_user_song_requests(self, user_id: int, limit: int = 50) -> List[Dict]:
        cursor = self.db.song_requests.find({"user_id": user_id}, {"_id": 0}).sort("_id", -1).limit(limit)
        return [dict(doc) async for doc in cursor]

    async def get_group_song_requests(self, chat_id: int, limit: int = 50) -> List[Dict]:
        cursor = self.db.song_requests.find({"chat_id": chat_id}, {"_id": 0}).sort("_id", -1).limit(limit)
        return [dict(doc) async for doc in cursor]

    async def get_total_songs_played(self) -> int:
        return await self.db.song_requests.count_documents({})

    async def clear_song_requests(self) -> None:
        await self.db.song_requests.delete_many({})

    # ─── ADMIN ALERT LOG ─────────────────────────────────────────────────────

    async def log_admin_alert(self, chat_id: int, chat_title: str,
                              bot_id: int, bot_name: str) -> None:
        await self.db.admin_alerts.insert_one(
            {"_id": await self._next_id("admin_alerts"), "chat_id": chat_id,
             "chat_title": chat_title, "bot_id": bot_id, "bot_name": bot_name,
             "alerted_at": time()}
        )

    async def get_admin_alerts(self, limit: int = 50) -> List[Dict]:
        cursor = self.db.admin_alerts.find({}, {"_id": 0}).sort("alerted_at", -1).limit(limit)
        return [dict(doc) async for doc in cursor]

    # ─── FILE REGISTRY ────────────────────────────────────────────────────────

    async def register_file(self, song_id: str, storage_path: str, public_url: str,
                            chat_id: int = 0, song_name: str = "") -> None:
        now = time()
        expires = now + 1800
        await self.db.file_registry.replace_one(
            {"_id": song_id},
            {"_id": song_id, "storage_path": storage_path, "public_url": public_url,
             "chat_id": chat_id, "song_name": song_name,
             "uploaded_at": now, "expires_at": expires},
            upsert=True,
        )

    async def unregister_file(self, song_id: str) -> None:
        await self.db.file_registry.delete_one({"_id": song_id})

    async def get_file_registry(self, limit: int = 50) -> List[Dict]:
        cursor = self.db.file_registry.find({}, {"_id": 0}).sort("uploaded_at", -1).limit(limit)
        return [dict(doc) async for doc in cursor]

    # ─── PREMIUM CHATS ────────────────────────────────────────────────────────

    async def set_premium(self, chat_id: int, granted_by: int = 0,
                          plan: str = "pro", days: int = 30) -> None:
        expires = time() + days * 86400
        await self.db.premium_chats.replace_one(
            {"_id": chat_id},
            {"_id": chat_id, "granted_by": granted_by, "expires_at": expires, "plan": plan},
            upsert=True,
        )

    async def is_premium(self, chat_id: int) -> bool:
        return await self.db.premium_chats.find_one(
            {"_id": chat_id, "expires_at": {"$gt": time()}}
        ) is not None

    async def get_premium_chats(self) -> List[Dict]:
        cursor = self.db.premium_chats.find({}, {"_id": 0}).sort("expires_at", -1)
        return [dict(doc) async for doc in cursor]

    # ─── API BASE METHODS ─────────────────────────────────────────────────────

    async def get_api(self) -> str:
        doc = await self.db.metadata.find_one({"_id": "api_base"})
        return doc.get("value") if doc else "https://youtube-downloader-1-v.vercel.app/api/download"

    async def set_api(self, value: str) -> None:
        await self.db.metadata.replace_one(
            {"_id": "api_base"}, {"_id": "api_base", "value": value}, upsert=True
        )

    # ─── WEB PASSWORD METHODS ────────────────────────────────────────────────

    async def get_web_password(self) -> str:
        doc = await self.db.metadata.find_one({"_id": "web_password"})
        if doc:
            return doc.get("value")
        from devverse import config
        return config.DASHBOARD_PASSWORD or ""

    async def set_web_password(self, value: str) -> None:
        await self.db.metadata.replace_one(
            {"_id": "web_password"}, {"_id": "web_password", "value": value}, upsert=True
        )

    # ─── CACHE LOADING ────────────────────────────────────────────────────────

    async def load_cache(self) -> None:
        from devverse import app

        await self.get_chats()
        await self.get_users()
        app.bl_users.update(await self.get_blacklisted())
        cursor = self.db.spies.find({}, {"_id": 1})
        app.spy_users.update({doc["_id"] async for doc in cursor})
        await self.get_logger()
        await self.get_sudoers()
        logger.info("Database cache loaded.")
