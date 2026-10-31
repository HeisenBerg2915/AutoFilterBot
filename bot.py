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
    LOG_CHANNEL
)

from database import init_db, close_db


# =========================
# CUSTOM PYROGRAM CLIENT
# =========================

class AutoFilterClient(Client):

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 1,
    ) -> AsyncGenerator[Message, None]:

        try:

            last_message_id = int(limit)

            current_message_id = max(
                1,
                int(offset)
            )

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
                range(
                    current_message_id,
                    batch_end + 1
                )
            )

            messages = await self.get_messages(
                chat_id,
                message_ids
            )

            if not isinstance(messages, (list, tuple)):

                messages = (
                    [messages]
                    if messages is not None
                    else []
                )

            for message in messages:

                yield message

            current_message_id = batch_end + 1


# =========================
# GLOBAL APP
# =========================

app = None


# =========================
# WEB SERVER
# =========================

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

    port = int(
        os.environ.get("PORT", 10000)
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(
        f"Web Server Running on Port {port}"
    )

    return runner


# =========================
# MAIN FUNCTION
# =========================

async def main():

    global app

    runner = None

    bot_started = False

    try:

        # DATABASE

        print("Connecting MongoDB...")

        await init_db()

        print("MongoDB Connected Successfully!")

        # WEB SERVER

        print("Starting Web Server...")

        runner = await start_web_server()

        # CREATE TELEGRAM CLIENT

        print("Creating Telegram Client...")

        app = AutoFilterClient(
            "AutoFilterBot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={
                "root": "plugins"
            },
        )

        # =========================
        # JOIN REQUEST CONFIGURATION
        # =========================

        app.req_link1 = (
            os.getenv("REQ_LINK1") or None
        )

        app.req_link2 = (
            os.getenv("REQ_LINK2") or None
        )

        print(
            "Channel 1 Join Request Link:",
            "Configured"
            if app.req_link1
            else "Not Configured"
        )

        print(
            "Channel 2 Join Request Link:",
            "Configured"
            if app.req_link2
            else "Not Configured"
        )

        if not app.req_link1 or not app.req_link2:

            print(
                "WARNING: Both Join Request Links "
                "must be configured!"
            )

        # =========================
        # START BOT
        # =========================

        print("Starting Telegram Bot...")

        await app.start()

        bot_started = True

        # =========================
        # LOAD LOG CHANNEL
        # =========================

        app.log_channel_id = None

        if LOG_CHANNEL:

            print("Loading Log Channel...")

            try:

                log_chat = await app.get_chat(
                    LOG_CHANNEL
                )

                app.log_channel_id = log_chat.id

                print(
                    "Log Channel Loaded Successfully:",
                    app.log_channel_id
                )

            except Exception as e:

                print(
                    f"Log Channel Loading Error: "
                    f"{type(e).__name__}: {e}"
                )

        else:

            print("LOG_CHANNEL Not Configured!")

        # =========================
        # BOT INFORMATION
        # =========================

        me = await app.get_me()

        print(
            "Bot Started Successfully!"
        )

        print(
            f"Bot Username: @{me.username}"
        )

        print(
            "Join Request System: Ready"
        )

        print(
            "Bot is waiting for messages..."
        )

        await idle()

    except Exception as e:

        print(
            f"Bot Error: {type(e).__name__}: {e}"
        )

        raise

    finally:

        if bot_started:

            await app.stop()

        if runner:

            await runner.cleanup()

        await close_db()

        print("Bot Stopped!")


# =========================
# RUN BOT
# =========================

if __name__ == "__main__":

    asyncio.run(main())
