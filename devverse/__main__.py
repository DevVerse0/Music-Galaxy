# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


import asyncio
import signal
import importlib
from contextlib import suppress

from devverse import (anon, app, config, db, logger,
                   stop, thumb, userbot, yt, boot)
from devverse.core.web import start_web
from devverse.plugins import all_modules


async def idle():
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()

async def main():
    await db.connect()
    # Start the Web Dashboard FIRST to pass Railway healthchecks immediately
    asyncio.create_task(start_web())
    logger.info(f"Dashboard starting on port {config.PORT}...")

    try:
        config.check()
    except SystemExit as e:
        logger.error(f"Bot failed to start: {e}")
        logger.warning("The dashboard is running, but the Bot will NOT be functional until you fix .env")
        # Keep process alive for the dashboard
        await idle()
        return

    await app.boot()
    try:
        await userbot.boot()
        await anon.boot()
    except Exception as e:
        logger.error(f"Failed to start Assistants/Calls: {e}")
        logger.warning("Bot will run without Voice Chat support.")

    await thumb.start()


    for module in all_modules:
        importlib.import_module(f"devverse.plugins.{module}")
    logger.info(f"Loaded {len(all_modules)} modules.")

    if config.COOKIES_URL:
        try:
            import os
            os.makedirs("devverse/cookies", exist_ok=True)
            await yt.save_cookies(config.COOKIES_URL)
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    if config.COOKIES:
        try:
            import os
            os.makedirs(os.path.dirname(config.COOKIES_FILE) or ".", exist_ok=True)
            with open(config.COOKIES_FILE, "w", encoding="utf-8") as f:
                f.write(config.COOKIES)
            logger.info("Cookies written from COOKIES env to %s", config.COOKIES_FILE)
        except Exception as e:
            logger.error(f"Failed to write COOKIES env: {e}")


    sudoers_list = await db.get_sudoers()
    app.sudoers.update(sudoers_list)
    app.bl_users.update(await db.get_blacklisted())
    logger.info(f"Loaded {len(app.sudoers)} sudo users.")



    await idle()
    await stop()


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass

