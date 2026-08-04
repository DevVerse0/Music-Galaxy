# -*- coding: utf-8 -*-
# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


import pyrogram

from devverse import config, logger


class AppFilter(pyrogram.filters.Filter, set):
    def __init__(self, *args):
        set.__init__(self, *args)
        pyrogram.filters.Filter.__init__(self)

    async def __call__(self, _, m: pyrogram.types.Message):

        if not m.from_user:
            return False
        return m.from_user.id in self


class Bot(pyrogram.Client):
    def __init__(self):
        super().__init__(
            name="MusicGalaxy",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            parse_mode=pyrogram.enums.ParseMode.HTML,
            max_concurrent_transmissions=7,
            link_preview_options=pyrogram.types.LinkPreviewOptions(is_disabled=True),
        )
        self.owner = config.OWNER_ID
        self.logger = config.LOGGER_ID
        
        self.sudoers = AppFilter({self.owner})
        self.bl_users = AppFilter()
        self.spy_users = AppFilter()

    @staticmethod
    def rnd_id(n: int = 10) -> int:
        import random
        return random.randint(10**(n-1), 10**n - 1)


    async def boot(self):
        """
        Starts the bot and performs initial setup.
        """
        await super().start()
        self.id = self.me.id
        self.name = self.me.first_name
        self.username = self.me.username
        self.mention = self.me.mention

        try:
            get = await self.get_chat_member(self.logger, self.id)
            if get.status != pyrogram.enums.ChatMemberStatus.ADMINISTRATOR:
                logger.warning("Bot is NOT an admin in the logger group. Logging might semi-fail.")
        except Exception as ex:
            logger.warning(f"Bot has failed to access the log group: {self.logger}. Reason: {ex}")

        
        # Register Commands in Telegram Menu
        try:
            await self.set_bot_commands([
                pyrogram.types.BotCommand("start", "🎵 Power Up Music Galaxy"),
                pyrogram.types.BotCommand("play", "🎶 Stream High-Quality Track"),
                pyrogram.types.BotCommand("commands", "📜 Complete Command Universe"),
                pyrogram.types.BotCommand("skip", "⏭️ Play Next Stream"),
                pyrogram.types.BotCommand("stop", "⏹️ Kill Current Stream"),
                pyrogram.types.BotCommand("ping", "📡 Check System Latency"),
                pyrogram.types.BotCommand("stats", "📊 View Analytics"),
                pyrogram.types.BotCommand("settings", "⚙️ Manage Configuration"),
                pyrogram.types.BotCommand("help", "❓ Intelligent Help HUB"),

            ])
            logger.info("Bot commands registered successfully.")
        except Exception as e:
            logger.error(f"Failed to register bot commands: {e}")

        logger.info(f"Bot started as @{self.username}")
        
        from devverse.core.dir import auto_clean
        import asyncio
        asyncio.create_task(auto_clean())



    async def exit(self):
        """
        Asynchronously stops the bot.
        """
        await super().stop()
        logger.info("Bot stopped.")

