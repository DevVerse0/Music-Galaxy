# -*- coding: utf-8 -*-
from os import getenv

class Config:
    def __init__(self):
        # ─── Database ──────────────────────────────────────────────

        self.API_ID = int(getenv("API_ID") or 0)
        self.API_HASH = getenv("API_HASH") or ""

        self.BOT_TOKEN = getenv("BOT_TOKEN") or ""
        self.DATABASE_URL = getenv("DATABASE_URL") or "database.db"
        self.DATABASE_MONGO = getenv("DATABASE_MONGO", "False").lower() == "true"
        self.MONGO_URI = getenv("MONGO_URI") or "mongodb://localhost:27017"

        self.LOGGER_ID = int(getenv("LOGGER_ID") or 0)
        self.OWNER_ID = int(getenv("OWNER_ID") or 0)
        self.OWNER_USERNAME = (getenv("OWNER_USERNAME", "Delete_ee") or "").lstrip("@").strip()
        self.MAINTENANCE: bool = getenv("MAINTENANCE", "False").lower() == "true"

        self.PORT = int(getenv("PORT", 6090))
        
        # Dashboard URL
        self.DASHBOARD_URL = getenv("DASHBOARD_URL", "")
        self.DASHBOARD_PASSWORD = getenv("DASHBOARD_PASSWORD", "")
        
        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT") or 60) * 60
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT") or 20)
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT") or 20)

        self.SESSION1 = getenv("SESSION1") or ""
        self.SESSION2 = getenv("SESSION2") or ""
        self.SESSION3 = getenv("SESSION3") or ""

        self.SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "")
        self.SUPPORT_CHAT = getenv("SUPPORT_CHAT", "")

        self.AUTO_LEAVE: bool = getenv("AUTO_LEAVE", "True").lower() == "true"
        self.AUTO_END: bool = getenv("AUTO_END", "True").lower() == "true"
    
        self.THUMB_GEN: bool = getenv("THUMB_GEN", "True").lower() == "true"
        self.VIDEO_PLAY: bool = getenv("VIDEO_PLAY", "True").lower() == "true"

        self.LANG_CODE = getenv("LANG_CODE", "en")

        self.COOKIES_URL = [
            url.strip() for url in getenv("COOKIES_URL", "").split(" ")
            if url.strip()
        ]
        self.COOKIES_FILE = getenv("COOKIES_FILE", "cookies.txt")
        self.DEFAULT_THUMB = getenv("DEFAULT_THUMB", "")
        self.PING_IMG = getenv("PING_IMG", "")
        self.START_IMG = getenv("START_IMG", "")

        # ─── Download API (for platforms where yt-dlp is blocked, e.g. Render) ──
        self.DOWNLOAD_API = getenv("DOWNLOAD_API", "False").lower() == "true"
        self.DOWNLOAD_API_URL = getenv("DOWNLOAD_API_URL") or ""
        self.DOWNLOAD_API_KEY = getenv("DOWNLOAD_API_KEY") or ""

        # ─── Cookies (for YouTube bot-check bypass) ──
        # COOKIES_URL fetches cookies.txt from URL(s); COOKIES holds raw content.
        self.COOKIES = getenv("COOKIES") or ""

    def check(self):
        missing = [
            var
            for var in ["API_ID", "API_HASH", "BOT_TOKEN", "LOGGER_ID", "OWNER_ID"]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

