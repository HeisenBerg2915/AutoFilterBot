import os
import asyncio

from aiohttp import web
from pyrogram import Client, idle

from config import API_ID, API_HASH, BOT_TOKEN
from database import init_db, close_db


# Telegram Bot
app = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins={"root": "plugins"}
)


# Web Server
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


# Main Function
async def main():

    runner = None

    try:
        print("Connecting MongoDB...")

        await init_db()

        print("Starting Web Server...")

        runner = await start_web_server()

        print("Starting Telegram Bot...")

        await app.start()

        me = await app.get_me()

        print("Bot Started Successfully!")
        print(f"Bot Username: @{me.username}")

        await idle()

    except Exception as e:
        print(f"Bot Error: {e}")

    finally:

        if app.is_connected:
            await app.stop()

        if runner:
            await runner.cleanup()

        await close_db()

        print("Bot Stopped!")


if __name__ == "__main__":
    asyncio.run(main())
