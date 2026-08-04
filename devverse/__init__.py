# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


from dotenv import load_dotenv
load_dotenv()

import time
import asyncio
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    format="%(asctime)s | %(levelname)-7s | %(name)s > %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        RotatingFileHandler("log.txt", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("ntgcalls").setLevel(logging.CRITICAL)
logging.getLogger("aiosqlite").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


__version__ = "5.0.0"

from config import Config

config = Config()
tasks = []
boot = time.time()

from devverse.core.bot import Bot
app = Bot()

from devverse.core.dir import ensure_dirs
ensure_dirs()

from devverse.core.userbot import Userbot
userbot = Userbot()

from devverse.core.database import Database
db = Database()

from devverse.core.lang import Language
lang = Language()

from devverse.core.telegram import Telegram
from devverse.core.youtube import YouTube
tg = Telegram()
yt = YouTube()

from devverse.helpers import Queue, Thumbnail
queue = Queue()
thumb = Thumbnail()

from devverse.core.calls import TgCall
anon = TgCall()



async def stop() -> None:
    logger.info("Stopping...")
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.exceptions.CancelledError:
            pass

    await app.exit()
    await userbot.exit()
    await db.close()
    await thumb.close()
    await yt.close()

    logger.info("Stopped.\n")

