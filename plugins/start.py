from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import app
from database import users_col, files_col
from config import LOG_CHANNEL, UPDATE_CHANNEL, UPDATE_GROUP


@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):

    user = message.from_user
    user_id = user.id

    # Register User
    old_user = await users_col.find_one({"id": user_id})

    if not old_user:

        await users_col.insert_one({
            "id": user_id,
            "first_name": user.first_name,
            "username": user.username,
            "is_bot": user.is_bot
        })

        # New User Log
        if LOG_CHANNEL:
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"🆕 **New User Started Bot!**\n\n"
                    f"👤 Name: {user.mention}\n"
                    f"🆔 ID: `{user_id}`\n"
                    f"📛 Username: @{user.username or 'None'}"
                )
            except Exception as e:
                print(f"Log Error: {e}")

    # Deep Link File Delivery
    if len(message.command) > 1:

        payload = message.command[1]

        if payload.startswith("file_"):

            try:
                parts = payload.split("_", 2)

                chat_id = int(parts[1])
                message_id = int(parts[2])

                file = await files_col.find_one({
                    "chat_id": chat_id,
                    "message_id": message_id
                })

                if not file:
                    await message.reply_text(
                        "❌ File Not Found!"
                    )
                    return

                await client.copy_message(
                    chat_id=user_id,
                    from_chat_id=chat_id,
                    message_id=message_id
                )

                return

            except Exception as e:
                print(f"File Delivery Error: {e}")

                await message.reply_text(
                    "❌ Unable to Send File.\n"
                    "Please Try Again Later."
                )

                return

    # Welcome Message
    text = (
        f"👋 Hello {user.mention}!\n\n"
        "🎬 Welcome to Auto Filter Bot!\n\n"
        "🔍 Search your favourite movies and files "
        "easily using our bot.\n\n"
        "👇 Use the buttons below!"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add Me To Your Group",
                url=f"https://t.me/{client.me.username}?startgroup=true"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 Join To Group",
                url=UPDATE_GROUP
            ),
            InlineKeyboardButton(
                "📢 Join To Channel",
                url=UPDATE_CHANNEL
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Stats",
                callback_data="stats"
            )
        ]
    ])

    await message.reply_text(
        text,
        reply_markup=buttons
    )
