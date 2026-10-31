import asyncio
from html import escape

from bson import ObjectId

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    users_col,
    files_col,
    files_col2,
    files_col3,
    reqone,
    reqtwo
)

from tag_cleaner import clean_file_name

from config import LOG_CHANNEL, UPDATE_CHANNEL, UPDATE_GROUP


# =========================
# DATABASE COLLECTIONS
# =========================

DATABASES = {
    "1": files_col,
    "2": files_col2,
    "3": files_col3
}


# =========================
# LOG CHANNEL
# =========================

async def send_log(client, text):

    log_chat_id = getattr(
        client,
        "log_channel_id",
        None
    )

    if not LOG_CHANNEL:
        return

    if not log_chat_id:

        print("Log Channel Not Available!")
        return

    try:

        await client.send_message(
            chat_id=log_chat_id,
            text=text
        )

    except Exception as e:

        print(
            f"Delivery Log Error: "
            f"{type(e).__name__}: {e}"
        )


# =========================
# CHECK JOIN REQUESTS
# =========================

async def check_join_requests(user_id):

    try:

        request_one = await reqone.find_one({
            "user_id": user_id
        })

        request_two = await reqtwo.find_one({
            "user_id": user_id
        })

        return bool(request_one and request_two)

    except Exception as e:

        print(f"Join Request Check Error: {e}")

        return False


# =========================
# JOIN BUTTONS
# =========================

def join_request_buttons(client, payload):

    link1 = getattr(client, "req_link1", None)
    link2 = getattr(client, "req_link2", None)

    buttons = []

    if link1:

        buttons.append([
            InlineKeyboardButton(
                "📢 JOIN CHANNEL 1",
                url=link1
            )
        ])

    if link2:

        buttons.append([
            InlineKeyboardButton(
                "📢 JOIN CHANNEL 2",
                url=link2
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔄 TRY AGAIN",
            callback_data=f"try:{payload}"
        )
    ])

    return InlineKeyboardMarkup(buttons)


# =========================
# GET FILE
# =========================

async def get_file(payload):

    try:

        if payload.startswith(("f1_", "f2_", "f3_")):

            db_number = payload[1]
            document_id = payload[3:]

            collection = DATABASES.get(db_number)

            if collection is None:
                return None

            if not ObjectId.is_valid(document_id):
                return None

            return await collection.find_one({
                "_id": ObjectId(document_id)
            })

        elif payload.startswith("f_"):

            document_id = payload[2:]

            if not ObjectId.is_valid(document_id):
                return None

            return await files_col.find_one({
                "_id": ObjectId(document_id)
            })

        elif payload.startswith("file_"):

            parts = payload.split("_", 2)

            if len(parts) != 3:
                return None

            chat_id = int(parts[1])
            message_id = int(parts[2])

            return await files_col.find_one({
                "chat_id": chat_id,
                "message_id": message_id
            })

    except Exception as e:

        print(f"Get File Error: {e}")

    return None


# =========================
# AUTO DELETE
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

        print(f"Auto Deleted: {user_id}")

    except Exception as e:

        print(f"Auto Delete Error: {e}")


# =========================
# SEND FILE
# =========================

async def send_file_to_user(client, user, file):

    user_id = user.id

    file_id = file.get("file_id")

    if not file_id:
        raise ValueError("File ID Not Available")

    original_name = (
        file.get("file_name")
        or "Unknown File"
    )

    file_name = clean_file_name(original_name)

    file_size = file.get("file_size", 0) or 0

    size_mb = file_size / (1024 * 1024)

    if size_mb >= 1024:
        size_text = f"{size_mb / 1024:.2f} GB"
    else:
        size_text = f"{size_mb:.2f} MB"

    file_caption = (
        f"<code>{escape(str(file_name))}\n\n"
        f"🔘 size - {size_text}</code>"
    )

    # SEND FILE

    sent_file = await client.send_cached_media(
        chat_id=user_id,
        file_id=file_id,
        caption=file_caption,
        parse_mode=ParseMode.HTML
    )

    # DELIVERY LOG

    log_text = (
        "📥 FILE DELIVERY SUCCESS\n\n"
        f"👤 User: {escape(user.first_name or 'Unknown')}\n"
        f"🆔 User ID: {user_id}\n"
        f"📛 Username: @{escape(user.username or 'None')}\n"
        f"📁 File: {escape(str(file_name))}\n\n"
        "✅ File successfully sent."
    )

    await send_log(
        client,
        log_text
    )

    # IMPORTANT MESSAGE

    sent_notice = None

    try:

        sent_notice = await client.send_message(
            chat_id=user_id,
            text=(
                "‼️ IMPORTANT ‼️\n\n"
                "ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ 2 mins\n\n"
                "ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ "
                "ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs."
            )
        )

    except Exception as e:

        print(f"Important Message Error: {e}")

    # AUTO DELETE

    asyncio.create_task(
        auto_delete_file(
            client,
            user_id,
            sent_file.id,
            sent_notice.id if sent_notice else None
        )
    )

    return sent_file


# =========================
# WELCOME KEYBOARD
# =========================

def welcome_buttons(client):

    return InlineKeyboardMarkup([
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
                "⚙️ Commands",
                callback_data="commands"
            ),
            InlineKeyboardButton(
                "📊 Stats",
                callback_data="stats"
            )
        ]
    ])


# =========================
# START COMMAND
# =========================

@Client.on_message(
    filters.command("start") & filters.private
)
async def start_command(client, message):

    user = message.from_user
    user_id = user.id

    # REGISTER USER

    old_user = await users_col.find_one({
        "id": user_id
    })

    if not old_user:

        await users_col.insert_one({
            "id": user_id,
            "first_name": user.first_name,
            "username": user.username,
            "is_bot": user.is_bot
        })

        await send_log(
            client,
            (
                "🆕 NEW USER STARTED BOT!\n\n"
                f"👤 Name: {escape(user.first_name or 'Unknown')}\n"
                f"🆔 ID: {user_id}\n"
                f"📛 Username: @{escape(user.username or 'None')}"
            )
        )

    # FILE DEEP LINK

    if len(message.command) > 1:

        payload = message.command[1]

        if payload.startswith(
            ("f1_", "f2_", "f3_", "f_", "file_")
        ):

            try:

                file = await get_file(payload)

                if not file:

                    await message.reply_text(
                        "❌ File Not Found!"
                    )

                    return

                joined = await check_join_requests(user_id)

                if not joined:

                    await message.reply_text(
                        (
                            "⚠️ JOIN REQUEST REQUIRED\n\n"
                            "Please send Join Requests to both channels.\n\n"
                            "After sending both requests, "
                            "press TRY AGAIN."
                        ),
                        reply_markup=join_request_buttons(
                            client,
                            payload
                        )
                    )

                    return

                await send_file_to_user(
                    client,
                    user,
                    file
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

    # NORMAL START MESSAGE

    text = (
        f"👋 Hello {user.mention}!\n\n"
        "🎬 Welcome to Auto Filter Bot!\n\n"
        "🔍 Search your favourite movies and files easily."
    )

    await message.reply_text(
        text,
        reply_markup=welcome_buttons(client)
    )


# =========================
# COMMANDS CALLBACK
# =========================

@Client.on_callback_query(
    filters.regex(r"^commands$")
)
async def commands_callback(client, callback_query):

    text = (
        "📚 **BOT COMMANDS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👤 **USER COMMANDS**\n\n"
        "/start - Start the bot\n\n"
        "🔐 **ADMIN COMMANDS**\n\n"
        "/id - Get ID\n"
        "/missing - Missing Movies\n"
        "/index - Index Files\n"
        "/delete - Delete File\n"
        "/deleteall - Delete All Files\n"
        "/totalreq - Total Requests\n"
        "/purge_one - Clear Channel 1 Requests\n"
        "/purge_two - Clear Channel 2 Requests\n"
        "/reqlinks - Get Request Links\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Admin Commands can only be used by Admins."
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 BACK",
                callback_data="back_home"
            )
        ]
    ])

    await callback_query.message.edit_text(
        text,
        reply_markup=buttons
    )

    await callback_query.answer()


# =========================
# BACK TO HOME
# =========================

@Client.on_callback_query(
    filters.regex(r"^back_home$")
)
async def back_home_callback(client, callback_query):

    user = callback_query.from_user

    text = (
        f"👋 Hello {user.mention}!\n\n"
        "🎬 Welcome to Auto Filter Bot!\n\n"
        "🔍 Search your favourite movies and files easily."
    )

    await callback_query.message.edit_text(
        text,
        reply_markup=welcome_buttons(client)
    )

    await callback_query.answer()


# =========================
# TRY AGAIN CALLBACK
# =========================

@Client.on_callback_query(
    filters.regex(r"^try:")
)
async def try_again_callback(client, callback_query):

    user = callback_query.from_user
    user_id = user.id

    payload = callback_query.data.split(
        ":",
        1
    )[1]

    # CHECK BOTH REQUESTS

    joined = await check_join_requests(user_id)

    if not joined:

        await callback_query.answer(
            "❌ Both Join Requests are not found!",
            show_alert=True
        )

        return

    # FIND FILE

    file = await get_file(payload)

    if not file:

        await callback_query.answer(
            "❌ File Not Found!",
            show_alert=True
        )

        return

    # SEND FILE

    try:

        await callback_query.answer(
            "✅ Verified! Sending File..."
        )

        await send_file_to_user(
            client,
            user,
            file
        )

        await callback_query.message.edit_text(
            (
                "✅ JOIN REQUESTS VERIFIED!\n\n"
                "📁 Your file has been sent to your PM."
            )
        )

    except Exception as e:

        print(
            f"Try Again Delivery Error: "
            f"{type(e).__name__}: {e}"
        )

        await callback_query.message.reply_text(
            "❌ File Delivery Failed. Please try again."
        )
