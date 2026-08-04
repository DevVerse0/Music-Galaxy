# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee — by @Delete_ee

import sqlite3
import aiosqlite
from random import randint
from time import time
from typing import List, Set, Union, Optional, Dict

from devverse import config, logger, userbot



class Database:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

        # Caches
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

    async def connect(self) -> None:
        """Initialize the SQLite database and create tables."""
        try:
            start = time()
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            await self._create_tables()
            logger.info(f"Database connection successful. ({time() - start:.2f}s)")
            await self.load_cache()
        except Exception as e:
            logger.exception("Database connection failed")
            raise SystemExit(f"Database connection failed: {type(e).__name__}") from e

    async def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        queries = [
            "CREATE TABLE IF NOT EXISTS auth (chat_id INTEGER, user_id INTEGER, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS assistant (chat_id INTEGER PRIMARY KEY, num INTEGER)",
            "CREATE TABLE IF NOT EXISTS blacklist_chats (chat_id INTEGER PRIMARY KEY)",
            "CREATE TABLE IF NOT EXISTS blacklist_users (user_id INTEGER PRIMARY KEY)",
            "CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, cmd_delete BOOLEAN DEFAULT 0, admin_play BOOLEAN DEFAULT 1)",
            "CREATE TABLE IF NOT EXISTS lang (chat_id INTEGER PRIMARY KEY, lang TEXT)",
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)",
            "CREATE TABLE IF NOT EXISTS sudoers (user_id INTEGER PRIMARY KEY)",
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)",
            "CREATE TABLE IF NOT EXISTS gbans (user_id INTEGER PRIMARY KEY, reason TEXT)",
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                user_id INTEGER,
                chat_id INTEGER,
                extra_info TEXT,
                timestamp REAL
            )""",
            # Advanced spy system: user_id + destination group
            """CREATE TABLE IF NOT EXISTS spies (
                user_id INTEGER PRIMARY KEY,
                dest_group_id INTEGER DEFAULT 0,
                added_at REAL DEFAULT 0
            )""",
            # Advanced user info storage
            """CREATE TABLE IF NOT EXISTS users_info (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_bot INTEGER DEFAULT 0,
                join_date REAL DEFAULT 0,
                last_seen REAL DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                is_restricted INTEGER DEFAULT 0
            )""",
            # Advanced group info storage
            """CREATE TABLE IF NOT EXISTS groups_info (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                username TEXT,
                member_count INTEGER DEFAULT 0,
                description TEXT,
                join_date REAL DEFAULT 0,
                last_active REAL DEFAULT 0,
                total_songs_played INTEGER DEFAULT 0,
                is_blacklisted INTEGER DEFAULT 0
            )""",
            # Song request log
            """CREATE TABLE IF NOT EXISTS song_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                chat_id INTEGER,
                chat_title TEXT,
                song_name TEXT,
                song_link TEXT,
                duration TEXT,
                requested_at REAL DEFAULT 0
            )""",
            # Restricted users (from bot commands)
            "CREATE TABLE IF NOT EXISTS restricted_users (user_id INTEGER PRIMARY KEY, reason TEXT, restricted_at REAL DEFAULT 0)",
            # Admin-not-in-chat alert log
            """CREATE TABLE IF NOT EXISTS admin_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                chat_title TEXT,
                bot_id INTEGER,
                bot_name TEXT,
                alerted_at REAL DEFAULT 0
            )""",
            # File registry
            """CREATE TABLE IF NOT EXISTS file_registry (
                song_id TEXT PRIMARY KEY,
                storage_path TEXT,
                public_url TEXT,
                chat_id INTEGER DEFAULT 0,
                song_name TEXT,
                uploaded_at REAL DEFAULT 0,
                expires_at REAL DEFAULT 0
            )""",
            # Subscription / premium groups
            """CREATE TABLE IF NOT EXISTS premium_chats (
                chat_id INTEGER PRIMARY KEY,
                granted_by INTEGER DEFAULT 0,
                expires_at REAL DEFAULT 0,
                plan TEXT DEFAULT 'free'
            )""",
            # Per-song play stats
            """CREATE TABLE IF NOT EXISTS song_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_name TEXT,
                play_count INTEGER DEFAULT 1,
                last_played REAL DEFAULT 0
            )""",
            # Maintenance schedule
            """CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT,
                target_id INTEGER DEFAULT 0,
                run_at REAL DEFAULT 0,
                done INTEGER DEFAULT 0
            )""",
        ]

        for query in queries:
            await self._conn.execute(query)

        # Migrations: add columns if missing
        migrations = [
            "ALTER TABLE audit_log ADD COLUMN extra_info TEXT",
            "ALTER TABLE spies ADD COLUMN dest_group_id INTEGER DEFAULT 0",
            "ALTER TABLE spies ADD COLUMN added_at REAL DEFAULT 0",
        ]
        for m in migrations:
            try:
                await self._conn.execute(m)
            except Exception:
                pass

        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed.")

    async def execute(self, query: str, *args):
        async with self._conn.execute(query, args) as cursor:
            await self._conn.commit()
            return cursor

    async def fetchall(self, query: str, *args):
        async with self._conn.execute(query, args) as cursor:
            return await cursor.fetchall()

    async def fetchone(self, query: str, *args):
        async with self._conn.execute(query, args) as cursor:
            return await cursor.fetchone()

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
            rows = await self.fetchall("SELECT user_id FROM auth WHERE chat_id = ?", chat_id)
            self.auth[chat_id] = {row['user_id'] for row in rows}
        return self.auth[chat_id]

    async def is_auth(self, chat_id: int, user_id: int) -> bool:
        return user_id in await self._get_auth(chat_id)

    async def add_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id not in users:
            users.add(user_id)
            await self.execute("INSERT OR IGNORE INTO auth (chat_id, user_id) VALUES (?, ?)", chat_id, user_id)

    async def rm_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id in users:
            users.discard(user_id)
            await self.execute("DELETE FROM auth WHERE chat_id = ? AND user_id = ?", chat_id, user_id)

    # ─── ASSISTANT METHODS ────────────────────────────────────────────────────

    async def set_assistant(self, chat_id: int) -> int:
        if not userbot.clients:
            num = 1
        else:
            num = randint(1, len(userbot.clients))
        await self.execute("INSERT OR REPLACE INTO assistant (chat_id, num) VALUES (?, ?)", chat_id, num)
        self.assistant[chat_id] = num
        return num

    async def get_assistant(self, chat_id: int):
        from devverse import anon
        if chat_id not in self.assistant:
            row = await self.fetchone("SELECT num FROM assistant WHERE chat_id = ?", chat_id)
            num = row["num"] if row else await self.set_assistant(chat_id)
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
        client_map = {i+1: client for i, client in enumerate(userbot.clients)}
        return client_map.get(self.assistant[chat_id])

    # ─── BLACKLIST METHODS ────────────────────────────────────────────────────

    async def add_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            if chat_id not in self.blacklisted:
                self.blacklisted.append(chat_id)
                await self.execute("INSERT OR IGNORE INTO blacklist_chats (chat_id) VALUES (?)", chat_id)
        else:
            await self.execute("INSERT OR IGNORE INTO blacklist_users (user_id) VALUES (?)", chat_id)

    async def del_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            if chat_id in self.blacklisted:
                self.blacklisted.remove(chat_id)
                await self.execute("DELETE FROM blacklist_chats WHERE chat_id = ?", chat_id)
        else:
            await self.execute("DELETE FROM blacklist_users WHERE user_id = ?", chat_id)

    async def get_blacklisted(self, chat: bool = False) -> List[int]:
        if chat:
            if not self.blacklisted:
                rows = await self.fetchall("SELECT chat_id FROM blacklist_chats")
                self.blacklisted = [row['chat_id'] for row in rows]
            return self.blacklisted
        rows = await self.fetchall("SELECT user_id FROM blacklist_users")
        return [row['user_id'] for row in rows]

    # ─── CHAT METHODS ─────────────────────────────────────────────────────────

    async def is_chat(self, chat_id: int) -> bool:
        return chat_id in self.chats

    async def add_chat(self, chat_id: int) -> None:
        if not await self.is_chat(chat_id):
            self.chats.append(chat_id)
            await self.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", chat_id)

    async def rm_chat(self, chat_id: int) -> None:
        if await self.is_chat(chat_id):
            self.chats.remove(chat_id)
            await self.execute("DELETE FROM chats WHERE chat_id = ?", chat_id)

    async def get_chats(self) -> List[int]:
        if not self.chats:
            rows = await self.fetchall("SELECT chat_id FROM chats")
            self.chats = [row['chat_id'] for row in rows]
        return self.chats

    # ─── COMMAND DELETE ───────────────────────────────────────────────────────

    async def get_cmd_delete(self, chat_id: int) -> bool:
        if chat_id not in self.cmd_delete:
            row = await self.fetchone("SELECT cmd_delete FROM chats WHERE chat_id = ?", chat_id)
            if row and row['cmd_delete']:
                self.cmd_delete.append(chat_id)
        return chat_id in self.cmd_delete

    async def set_cmd_delete(self, chat_id: int, delete: bool = False) -> None:
        if delete:
            if chat_id not in self.cmd_delete:
                self.cmd_delete.append(chat_id)
        else:
            if chat_id in self.cmd_delete:
                self.cmd_delete.remove(chat_id)
        await self.execute("INSERT OR REPLACE INTO chats (chat_id, cmd_delete) VALUES (?, ?)", chat_id, int(delete))

    # ─── LANGUAGE METHODS ─────────────────────────────────────────────────────

    async def set_lang(self, chat_id: int, lang_code: str):
        await self.execute("INSERT OR REPLACE INTO lang (chat_id, lang) VALUES (?, ?)", chat_id, lang_code)
        self.lang[chat_id] = lang_code

    async def get_lang(self, chat_id: int) -> str:
        if chat_id not in self.lang:
            row = await self.fetchone("SELECT lang FROM lang WHERE chat_id = ?", chat_id)
            self.lang[chat_id] = row['lang'] if row else config.LANG_CODE
        return self.lang.get(chat_id, config.LANG_CODE)

    # ─── LOGGER METHODS ───────────────────────────────────────────────────────

    async def is_logger(self) -> bool:
        return self.logger_status

    async def get_logger(self) -> bool:
        row = await self.fetchone("SELECT value FROM metadata WHERE key = 'logger'")
        if row:
            self.logger_status = row['value'] == 'True'
        return self.logger_status

    async def set_logger(self, status: bool) -> None:
        self.logger_status = status
        await self.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('logger', ?)", str(status))

    # ─── PLAY MODE METHODS ────────────────────────────────────────────────────

    async def get_play_mode(self, chat_id: int) -> bool:
        if chat_id not in self.admin_play:
            row = await self.fetchone("SELECT admin_play FROM chats WHERE chat_id = ?", chat_id)
            if row and row['admin_play']:
                self.admin_play.append(chat_id)
        return chat_id in self.admin_play

    async def set_play_mode(self, chat_id: int, remove: bool = False) -> None:
        if remove:
            if chat_id in self.admin_play:
                self.admin_play.remove(chat_id)
        else:
            if chat_id not in self.admin_play:
                self.admin_play.append(chat_id)
        await self.execute("INSERT OR REPLACE INTO chats (chat_id, admin_play) VALUES (?, ?)", chat_id, int(not remove))

    # ─── SUDO METHODS ─────────────────────────────────────────────────────────

    async def add_sudo(self, user_id: int) -> None:
        if user_id not in self.sudoers:
            self.sudoers.append(user_id)
            await self.execute("INSERT OR IGNORE INTO sudoers (user_id) VALUES (?)", user_id)

    async def del_sudo(self, user_id: int) -> None:
        if user_id in self.sudoers:
            self.sudoers.remove(user_id)
            await self.execute("DELETE FROM sudoers WHERE user_id = ?", user_id)

    async def get_sudoers(self) -> List[int]:
        if not self.sudoers:
            rows = await self.fetchall("SELECT user_id FROM sudoers")
            self.sudoers = [row['user_id'] for row in rows]
        return self.sudoers

    # ─── USER METHODS ─────────────────────────────────────────────────────────

    async def is_user(self, user_id: int) -> bool:
        return user_id in self.users

    async def add_user(self, user_id: int) -> None:
        if not await self.is_user(user_id):
            self.users.append(user_id)
            await self.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", user_id)

    async def rm_user(self, user_id: int) -> None:
        if await self.is_user(user_id):
            self.users.remove(user_id)
            await self.execute("DELETE FROM users WHERE user_id = ?", user_id)

    async def get_users(self) -> List[int]:
        if not self.users:
            rows = await self.fetchall("SELECT user_id FROM users")
            self.users = [row['user_id'] for row in rows]
        return self.users

    # ─── GBAN METHODS ─────────────────────────────────────────────────────────

    async def add_gban(self, user_id: int, reason: str = None) -> None:
        await self.execute("INSERT OR REPLACE INTO gbans (user_id, reason) VALUES (?, ?)", user_id, reason)

    async def del_gban(self, user_id: int) -> None:
        await self.execute("DELETE FROM gbans WHERE user_id = ?", user_id)

    async def get_gbans(self) -> List[int]:
        rows = await self.fetchall("SELECT user_id FROM gbans")
        return [row['user_id'] for row in rows]

    async def get_gban_reason(self, user_id: int) -> Optional[str]:
        row = await self.fetchone("SELECT reason FROM gbans WHERE user_id = ?", user_id)
        return row['reason'] if row else None

    # ─── AUDIT LOG METHODS ────────────────────────────────────────────────────

    async def add_audit_log(self, action: str, user_id: int = 0, chat_id: int = 0, extra_info: str = None) -> None:
        await self.execute(
            "INSERT INTO audit_log (action, user_id, chat_id, extra_info, timestamp) VALUES (?, ?, ?, ?, ?)",
            action, user_id, chat_id, extra_info, time()
        )

    async def get_audit_logs(self, limit: int = 100) -> List[sqlite3.Row]:
        return await self.fetchall("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", limit)

    async def clear_audit_logs(self) -> None:
        await self.execute("DELETE FROM audit_log")

    # ─── ADVANCED SPY SYSTEM ─────────────────────────────────────────────────
    # Spy: user_id + destination group_id where logs go

    async def add_spy(self, user_id: int, dest_group_id: int = 0) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO spies (user_id, dest_group_id, added_at) VALUES (?, ?, ?)",
            user_id, dest_group_id, time()
        )

    async def del_spy(self, user_id: int) -> None:
        await self.execute("DELETE FROM spies WHERE user_id = ?", user_id)

    async def get_spies(self) -> List[int]:
        rows = await self.fetchall("SELECT user_id FROM spies")
        return [row['user_id'] for row in rows]

    async def get_spy_dest(self, user_id: int) -> int:
        """Get destination group for a spy target (0 = use global LOGGER_ID)"""
        row = await self.fetchone("SELECT dest_group_id FROM spies WHERE user_id = ?", user_id)
        return row['dest_group_id'] if row else 0

    async def get_all_spies(self) -> List[Dict]:
        rows = await self.fetchall("SELECT user_id, dest_group_id, added_at FROM spies")
        return [dict(row) for row in rows]

    # ─── ADVANCED USER INFO ───────────────────────────────────────────────────

    async def update_user_info(self, user_id: int, username: str = None, first_name: str = None,
                               last_name: str = None, is_bot: bool = False) -> None:
        existing = await self.fetchone("SELECT user_id FROM users_info WHERE user_id = ?", user_id)
        if existing:
            await self.execute(
                """UPDATE users_info SET username=?, first_name=?, last_name=?, last_seen=?
                   WHERE user_id=?""",
                username, first_name, last_name, time(), user_id
            )
        else:
            await self.execute(
                """INSERT INTO users_info (user_id, username, first_name, last_name, is_bot, join_date, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                user_id, username, first_name, last_name, int(is_bot), time(), time()
            )


    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        row = await self.fetchone("SELECT * FROM users_info WHERE user_id = ?", user_id)
        return dict(row) if row else None

    async def get_all_users_info(self, limit: int = 200) -> List[Dict]:
        rows = await self.fetchall("SELECT * FROM users_info ORDER BY last_seen DESC LIMIT ?", limit)
        return [dict(row) for row in rows]

    async def increment_user_requests(self, user_id: int) -> None:
        await self.execute(
            "UPDATE users_info SET total_requests = total_requests + 1, last_seen = ? WHERE user_id = ?",
            time(), user_id
        )

    async def restrict_user(self, user_id: int, reason: str = "Manually restricted") -> None:
        await self.execute(
            "INSERT OR REPLACE INTO restricted_users (user_id, reason, restricted_at) VALUES (?, ?, ?)",
            user_id, reason, time()
        )
        await self.execute("UPDATE users_info SET is_restricted = 1 WHERE user_id = ?", user_id)

    async def unrestrict_user(self, user_id: int) -> None:
        await self.execute("DELETE FROM restricted_users WHERE user_id = ?", user_id)
        await self.execute("UPDATE users_info SET is_restricted = 0 WHERE user_id = ?", user_id)

    async def is_restricted(self, user_id: int) -> bool:
        row = await self.fetchone("SELECT user_id FROM restricted_users WHERE user_id = ?", user_id)
        return row is not None

    async def get_restricted_users(self) -> List[Dict]:
        rows = await self.fetchall("SELECT * FROM restricted_users ORDER BY restricted_at DESC")
        return [dict(row) for row in rows]

    # ─── ADVANCED GROUP INFO ──────────────────────────────────────────────────

    async def update_group_info(self, chat_id: int, title: str = None, username: str = None,
                                member_count: int = 0, description: str = None) -> None:
        existing = await self.fetchone("SELECT chat_id FROM groups_info WHERE chat_id = ?", chat_id)
        if existing:
            await self.execute(
                """UPDATE groups_info SET title=?, username=?, member_count=?, description=?, last_active=?
                   WHERE chat_id=?""",
                title, username, member_count, description, time(), chat_id
            )
        else:
            await self.execute(
                """INSERT INTO groups_info (chat_id, title, username, member_count, description, join_date, last_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                chat_id, title, username, member_count, description, time(), time()
            )


    async def get_group_info(self, chat_id: int) -> Optional[Dict]:
        row = await self.fetchone("SELECT * FROM groups_info WHERE chat_id = ?", chat_id)
        return dict(row) if row else None

    async def get_all_groups_info(self, limit: int = 200) -> List[Dict]:
        rows = await self.fetchall("SELECT * FROM groups_info ORDER BY last_active DESC LIMIT ?", limit)
        return [dict(row) for row in rows]

    async def increment_group_songs(self, chat_id: int) -> None:
        await self.execute(
            "UPDATE groups_info SET total_songs_played = total_songs_played + 1, last_active = ? WHERE chat_id = ?",
            time(), chat_id
        )

    # ─── SONG REQUEST LOG ─────────────────────────────────────────────────────

    async def log_song_request(self, user_id: int, username: str, first_name: str,
                                chat_id: int, chat_title: str, song_name: str,
                                song_link: str = None, duration: str = None) -> None:
        await self.execute(
            """INSERT INTO song_requests
               (user_id, username, first_name, chat_id, chat_title, song_name, song_link, duration, requested_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            user_id, username or "Unknown", first_name or "Unknown",
            chat_id, chat_title or "Unknown", song_name, song_link, duration, time()
        )
        await self.increment_user_requests(user_id)
        await self.increment_group_songs(chat_id)

    async def get_song_requests(self, limit: int = 100) -> List[Dict]:
        rows = await self.fetchall(
            "SELECT * FROM song_requests ORDER BY id DESC LIMIT ?", limit
        )
        return [dict(row) for row in rows]

    async def get_user_song_requests(self, user_id: int, limit: int = 50) -> List[Dict]:
        rows = await self.fetchall(
            "SELECT * FROM song_requests WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            user_id, limit
        )
        return [dict(row) for row in rows]

    async def get_group_song_requests(self, chat_id: int, limit: int = 50) -> List[Dict]:
        rows = await self.fetchall(
            "SELECT * FROM song_requests WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            chat_id, limit
        )
        return [dict(row) for row in rows]

    async def get_total_songs_played(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) as cnt FROM song_requests")
        return row['cnt'] if row else 0

    # ─── CACHE LOADING ────────────────────────────────────────────────────────

    # ─── ADMIN ALERT LOG ─────────────────────────────────────────────────────

    async def log_admin_alert(self, chat_id: int, chat_title: str,
                               bot_id: int, bot_name: str) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO admin_alerts (chat_id, chat_title, bot_id, bot_name, alerted_at) VALUES (?, ?, ?, ?, ?)",
            chat_id, chat_title, bot_id, bot_name, time()
        )


    async def get_admin_alerts(self, limit: int = 50) -> List[Dict]:
        rows = await self.fetchall(
            "SELECT * FROM admin_alerts ORDER BY alerted_at DESC LIMIT ?", limit
        )
        return [dict(row) for row in rows]

    # ─── FILE REGISTRY ────────────────────────────────────────────────────────

    async def register_file(self, song_id: str, storage_path: str, public_url: str,
                             chat_id: int = 0, song_name: str = "") -> None:
        import asyncio
        from time import time as _time
        expires = _time() + 1800
        await self.execute(
            "INSERT OR REPLACE INTO file_registry (song_id, storage_path, public_url, chat_id, song_name, uploaded_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            song_id, storage_path, public_url, chat_id, song_name, _time(), expires
        )


    async def unregister_file(self, song_id: str) -> None:
        import asyncio
        await self.execute("DELETE FROM file_registry WHERE song_id = ?", song_id)


    async def get_file_registry(self, limit: int = 50) -> List[Dict]:
        rows = await self.fetchall(
            "SELECT * FROM file_registry ORDER BY uploaded_at DESC LIMIT ?", limit
        )
        return [dict(row) for row in rows]

    # ─── PREMIUM CHATS ────────────────────────────────────────────────────────

    async def set_premium(self, chat_id: int, granted_by: int = 0,
                          plan: str = "pro", days: int = 30) -> None:
        from time import time as _t
        expires = _t() + days * 86400
        await self.execute(
            "INSERT OR REPLACE INTO premium_chats (chat_id, granted_by, expires_at, plan) VALUES (?, ?, ?, ?)",
            chat_id, granted_by, expires, plan
        )

    async def is_premium(self, chat_id: int) -> bool:
        from time import time as _t
        row = await self.fetchone(
            "SELECT expires_at FROM premium_chats WHERE chat_id = ? AND expires_at > ?", chat_id, _t()
        )
        return row is not None

    async def get_premium_chats(self) -> List[Dict]:
        rows = await self.fetchall("SELECT * FROM premium_chats ORDER BY expires_at DESC")
        return [dict(row) for row in rows]

    # ─── API BASE METHODS ──────────────────────────────────────────────────

    async def get_api(self) -> str:
        row = await self.fetchone("SELECT value FROM metadata WHERE key = 'api_base'")
        return row['value'] if row else "https://youtube-downloader-1-v.vercel.app/api/download"

    async def set_api(self, value: str) -> None:
        await self.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('api_base', ?)", value)

    # ─── WEB PASSWORD METHODS ─────────────────────────────────────────────

    async def get_web_password(self) -> str:
        row = await self.fetchone("SELECT value FROM metadata WHERE key = 'web_password'")
        if row:
            return row['value']
        from devverse import config
        return config.DASHBOARD_PASSWORD or ""

    async def set_web_password(self, value: str) -> None:
        await self.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('web_password', ?)", value)

    # ─── CACHE LOADING ────────────────────────────────────────────────────────

    async def load_cache(self) -> None:
        from devverse import app
        
        await self.get_chats()
        await self.get_users()
        app.bl_users.update(await self.get_blacklisted())
        # Load spy users into app cache
        spy_rows = await self.fetchall("SELECT user_id FROM spies")
        for row in spy_rows:
            app.spy_users.add(row['user_id'])
        await self.get_logger()
        await self.get_sudoers()
        logger.info("Database cache loaded.")

