import os
import asyncio
from typing import AsyncGenerator, Union

from aiohttp import web
from pyrogram import Client, idle
from pyrogram.types import Message

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    REQ_CHANNEL1,
    REQ_CHANNEL2,
    LOG_CHANNEL
)

from database import init_db, close_db


class AutoFilterClient(Client):
    """Pyrogram client with message-ID batch iteration."""

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 1,
    ) -> AsyncGenerator[Message, None]:

        try:
            last_message_id = int(limit)
            current_message_id = max(1, int(offset))

        except (TypeError, ValueError):
            raise ValueError(
                "limit and offset must be valid message IDs"
            )

        while current_message_id <= last_message_id:

            batch_end = min(
                current_message_id + 199,
                last_message_id
            )

            message_ids = list(
                range(current_message_id, batch_end + 1)
            )

            messages = await self.get_messages(
                chat_id,
                message_ids
            )

            if not isinstance(messages, (list, tuple)):
                messages = (
                    [messages] if messages is not None else []
                )

            for message in messages:
                yield message

            current_message_id = batch_end + 1


# Global Client
app = None


async def home(request):
    return web.Response(
        text="Auto Filter Bot is Running! 🚀"
    )


async def start_web_server():

    web_app = web.Application()

    web_app.router.add_get("/", home)
    web_app.router.add_get("/health", home)

    runner = web.AppRunner(web_app)

    await runner.setup()

    port = int(os.environ.get("PORT", 10000))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(f"Web Server Running on Port {port}")

    return runner


async def main():

    global app

    runner = None
    bot_started = False

    try:

        # MongoDB
        print("Connecting MongoDB...")

        await init_db()

        # Web Server
        print("Starting Web Server...")

        runner = await start_web_server()

        # Telegram Client
        print("Creating Telegram Client...")

        app = AutoFilterClient(
            "AutoFilterBot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"},
        )

        # Start Bot
        print("Starting Telegram Bot...")

        await app.start()

        bot_started = True

        # =================================
        # MANUAL JOIN REQUEST LINKS
        # =================================

        app.req_link1 = os.getenv("REQ_LINK1") or None
        app.req_link2 = os.getenv("REQ_LINK2") or None

        print(
            "Channel 1 Join Request Link:",
            "Configured" if app.req_link1 else "Not Configured"
        )

        print(
            "Channel 2 Join Request Link:",
            "Configured" if app.req_link2 else "Not Configured"
        )

        # =================================
        # CHANNEL CONFIGURATION
        # =================================

        print("Checking Channel Configuration...")

        print(
            "Channel 1 ID:",
            REQ_CHANNEL1 if REQ_CHANNEL1 else "Not Configured"
        )

        print(
            "Channel 2 ID:",
            REQ_CHANNEL2 if REQ_CHANNEL2 else "Not Configured"
        )

        print(
            "Log Channel:",
            LOG_CHANNEL if LOG_CHANNEL else "Not Configured"
        )

        # Bot Information
        me = await app.get_me()

        print("Bot Started Successfully!")

        print(f"Bot Username: @{me.username}")

        print("Bot is waiting for messages...")

        await idle()

    except Exception as e:

        print(f"Bot Error: {e}")

        raise

    finally:

        if bot_started:
            await app.stop()

        if runner:
            await runner.cleanup()

        await close_db()

        print("Bot Stopped!")


if __name__ == "__main__":
    asyncio.run(main())
