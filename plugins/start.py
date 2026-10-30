from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import users_col, files_col
from config import LOG_CHANNEL, UPDATE_CHANNEL, UPDATE_GROUP


@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message):

    user = message.from_user
    user_id = user.id

    # REGISTER USER
    old_user = await users_col.find_one({"id": user_id})

    if not old_user:
        await users_col.insert_one({
            "id": user_id,
            "first_name": user.first_name,
            "username": user.username,
            "is_bot": user.is_bot
        })

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

    # PRIVATE FILE DELIVERY
    if len(message.command) > 1:

        payload = message.command[1]

        if payload.startswith("file_"):

            try:
                parts = payload.split("_", 2)

                if len(parts) != 3:
                    await message.reply_text("❌ Invalid File Link!")
                    return

                chat_id = int(parts[1])
                message_id = int(parts[2])

                file = await files_col.find_one({
                    "chat_id": chat_id,
                    "message_id": message_id
                })

                if not file:
                    await message.reply_text("❌ File Not Found!")
                    return

                # USE TELEGRAM FILE ID
                file_id = file.get("file_id")

                if file_id:
                    await client.send_cached_media(
                        chat_id=user_id,
                        file_id=file_id
                    )

                else:
                    # FALLBACK: COPY ORIGINAL MESSAGE
                    await client.copy_message(
                        chat_id=user_id,
                        from_chat_id=chat_id,
                        message_id=message_id
                    )

                return

            except Exception as e:

                print(f"File Delivery Error: {type(e).__name__}: {e}")

                await message.reply_text(
                    "❌ Unable to Send File.\n\n"
                    "Please contact the bot admin."
                )

                return

    # NORMAL START MESSAGE
    text = (
        f"👋 Hello {user.mention}!\n\n"
        "🎬 Welcome to Auto Filter Bot!\n\n"
        "🔍 Search your favourite movies and files easily."
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
