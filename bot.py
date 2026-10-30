import asyncio
from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN
from database import init_db, close_db


# Bot Configuration
app = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins={"root": "plugins"}
)


async def main():
    print("Connecting to MongoDB...")

    await init_db()

    print("Starting Telegram Bot...")

    await app.start()

    me = await app.get_me()

    print(f"Bot Started Successfully!")
    print(f"Bot Username: @{me.username}")

    await idle()

    print("Stopping Bot...")

    await app.stop()
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
