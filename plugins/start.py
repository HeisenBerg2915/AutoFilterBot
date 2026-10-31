import asyncio
from html import escape
from pyrogram.enums import ParseMode

from bson import ObjectId

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    users_col,
    files_col,
    files_col2,
    files_col3
)

from config import LOG_CHANNEL, UPDATE_CHANNEL, UPDATE_GROUP


DATABASES = {
    "1": files_col,
    "2": files_col2,
    "3": files_col3
}


# =========================
# AUTO DELETE FUNCTION
# =========================

async def auto_delete_file(
    client,
    user_id,
    file_message_id,
    notice_message_id
):

    await asyncio.sleep(120)

    try:

        message_ids = [file_message_id]

        if notice_message_id:
            message_ids.append(notice_message_id)

        await client.delete_messages(
            chat_id=user_id,
            message_ids=message_ids
        )

        print(
            f"File and Important Message Auto Deleted: {user_id}"
        )

    except Exception as e:

        print(f"Auto Delete Error: {e}")


# =========================
# START COMMAND
# =========================

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

    # =========================
    # PRIVATE FILE DELIVERY
    # =========================

    if len(message.command) > 1:

        payload = message.command[1]

        try:

            file = None

            # NEW DATABASE-SPECIFIC FILE LINKS

            if payload.startswith(("f1_", "f2_", "f3_")):

                db_number = payload[1]
                document_id = payload[3:]

                collection = DATABASES.get(db_number)

                if collection is None:

                    await message.reply_text(
                        "❌ Database Not Available!"
                    )

                    return

                if not ObjectId.is_valid(document_id):

                    await message.reply_text(
                        "❌ Invalid File Link!"
                    )

                    return

                file = await collection.find_one({
                    "_id": ObjectId(document_id)
                })

            # OLD FILE LINK COMPATIBILITY

            elif payload.startswith("f_"):

                document_id = payload[2:]

                if not ObjectId.is_valid(document_id):

                    await message.reply_text(
                        "❌ Invalid File Link!"
                    )

                    return

                file = await files_col.find_one({
                    "_id": ObjectId(document_id)
                })

            # OLDER CHAT/MESSAGE LINK COMPATIBILITY

            elif payload.startswith("file_"):

                parts = payload.split("_", 2)

                if len(parts) != 3:

                    await message.reply_text(
                        "❌ Invalid File Link!"
                    )

                    return

                chat_id = int(parts[1])
                message_id = int(parts[2])

                file = await files_col.find_one({
                    "chat_id": chat_id,
                    "message_id": message_id
                })

            # =========================
            # SEND FILE
            # =========================

            if file is not None:

                file_id = file.get("file_id")

                if not file_id:

                    await message.reply_text(
                        "❌ File ID not available.\n\n"
                        "Admin needs to re-index this file."
                    )

                    return

                # FILE NAME

                file_name = (
                    file.get("file_name")
                    or "Unknown File"
                )

                # FILE SIZE

                file_size = file.get("file_size", 0) or 0

                size_mb = file_size / (1024 * 1024)

                if size_mb >= 1024:

                    size_text = f"{size_mb / 1024:.2f} GB"

                else:

                    size_text = f"{size_mb:.2f} MB"

                # MONOSPACE CAPTION

                file_caption = (
                    f"<code>{escape(str(file_name))}\n\n"
                    f"🔘 size - {size_text}</code>"
                )

                # SEND FILE WITH CAPTION

                sent_file = await client.send_cached_media(
                    chat_id=user_id,
                    file_id=file_id,
                    caption=file_caption,
                    parse_mode=ParseMode.HTML
                )

                # =========================
                # IMPORTANT MESSAGE
                # =========================

                important_text = (
                    "‼️ IMPORTANT ‼️\n\n"
                    "ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ 2 mins\n\n"
                    "ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ "
                    "ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ᴏʀ ᴀɴʏ "
                    "ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ."
                )

                # SEND IMPORTANT MESSAGE

                sent_notice = None

                try:

                    sent_notice = await client.send_message(
                        chat_id=user_id,
                        text=important_text
                    )

                except Exception as e:

                    print(f"Important Message Error: {e}")

                # =========================
                # SCHEDULE AUTO DELETE
                # =========================

                asyncio.create_task(
                    auto_delete_file(
                        client,
                        user_id,
                        sent_file.id,
                        sent_notice.id if sent_notice else None
                    )
                )

                return

            # FILE NOT FOUND

            if payload.startswith(
                ("f1_", "f2_", "f3_", "f_", "file_")
            ):

                await message.reply_text(
                    "❌ File Not Found!"
                )

                return

        except Exception as e:

            print(
                f"File Delivery Error: "
                f"{type(e).__name__}: {e}"
            )

            await message.reply_text(
                "❌ Unable to Send File.\n\n"
                "Please contact the bot admin."
            )

            return

    # =========================
    # NORMAL START MESSAGE
    # =========================

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
