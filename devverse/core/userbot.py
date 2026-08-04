# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee


from pyrogram import Client
from pyrogram.errors import AuthKeyUnregistered

from devverse import config, logger


class Userbot(Client):
    def __init__(self):
        """
        Initializes the userbot with multiple clients.

        This method sets up clients for the userbot using predefined session strings.
        Each client is assigned a unique name based on the key in the `clients` dictionary.
        """
        self.clients = []
        clients = {"one": "SESSION1", "two": "SESSION2", "three": "SESSION3"}
        for key, string_key in clients.items():
            name = f"devverseUB{key[-1]}"
            session = getattr(config, string_key)
            setattr(
                self,
                key,
                Client(
                    name=name,
                    api_id=config.API_ID,
                    api_hash=config.API_HASH,
                    session_string=session,
                ),
            )

    async def boot_client(self, num: int, ub: Client):
        """
        Boot a client and perform initial setup.
        Args:
            num (int): The client number to boot (1, 2, or 3).
            ub (Client): The userbot client instance.
        Raises:
            SystemExit: If the client fails to send a message in the log group.
        """
        clients = {
            1: self.one,
            2: self.two,
            3: self.three,
        }
        client = clients[num]
        try:
            await client.start()
            await client.send_message(config.LOGGER_ID, "Assistant Started")
        except AuthKeyUnregistered:
            logger.error(
                f"Assistant {num} session is invalid or expired (AUTH_KEY_UNREGISTERED). "
                f"Generate a new session string and update SESSION{num} in your .env file."
            )
            return
        except Exception as e:
            logger.error(f"Assistant {num} failed to boot. The Session might be banned/deactivated: {e}")
            return


        client.id = client.me.id
        client.name = client.me.first_name
        client.username = client.me.username
        client.mention = client.me.mention
        self.clients.append(client)
        try:
            await client.join_chat("delete_tee7")
        except Exception:
            pass
        display = client.username or client.name or client.id
        logger.info(f"Assistant {num} started as @{display}")

    async def boot(self):
        """
        Asynchronously starts the assistants.
        """
        if config.SESSION1:
            await self.boot_client(1, self.one)
        if config.SESSION2:
            await self.boot_client(2, self.two)
        if config.SESSION3:
            await self.boot_client(3, self.three)

    async def exit(self):
        """
        Asynchronously stops the assistants.
        """
        if config.SESSION1:
            await self.one.stop()
        if config.SESSION2:
            await self.two.stop()
        if config.SESSION3:
            await self.three.stop()
        logger.info("Assistants stopped.")

