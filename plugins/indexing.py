from uuid import uuid4

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL, ADMINS
from helpers.database_router import (
    save_file_to_databases,
    get_target_collections
)
from helpers.episode_filter import is_tv_episode


# Temporary request storage
index_requests = {}


# ----------------------------------
# SEND INDEXING REQUEST
# ----------------------------------

@Client.on_message(filters.command("index") & filters.private)
async def index_request(client, message):

    if len(message.command) < 2:
        await message.reply_text(
            "⚠️ ഉപയോഗം:\n/index @channelusername"
        )
        return

    if not LOG_CHANNEL:
        await message.reply_text(
            "❌ LOG_CHANNEL configure ചെയ്തിട്ടില്ല."
        )
        return

    channel_link = message.text.split(maxsplit=1)[1].strip()

    request_id = uuid4().hex[:10]

    index_requests[request_id] = {
        "user_id": message.from_user.id,
        "channel": channel_link,
        "status": "pending",
        "database": None,
        "cancelled": False
    }

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ ACCEPT",
                callback_data=f"idx_accept:{request_id}"
            ),
            InlineKeyboardButton(
                "❌ REJECT",
                callback_data=f"idx_reject:{request_id}"
            )
        ]
    ])

    try:
        await client.send_message(
            LOG_CHANNEL,
            f"📥 **New Indexing Request**\n\n"
            f"👤 User: {message.from_user.mention}\n"
            f"🆔 User ID: `{message.from_user.id}`\n"
            f"🔗 Channel: `{channel_link}`\n"
            f"📝 Request ID: `{request_id}`",
            reply_markup=buttons
        )

        await message.reply_text(
            "✅ Indexing Request Moderator-ന് അയച്ചു."
        )

    except Exception as e:

        index_requests.pop(request_id, None)

        print(f"Index Request Error: {e}")

        await message.reply_text(
            "❌ Request അയക്കാൻ കഴിഞ്ഞില്ല."
        )


# ----------------------------------
# ACCEPT / REJECT REQUEST
# ----------------------------------

@Client.on_callback_query(
    filters.regex(r"^idx_(accept|reject):")
)
async def indexing_approval(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:
        await query.answer(
            "⛔ നിങ്ങൾക്ക് അനുമതിയില്ല!",
            show_alert=True
        )
        return

    action, request_id = query.data.split(":", 1)

    request = index_requests.get(request_id)

    if not request or request["status"] != "pending":
        await query.answer(
            "❌ Request ലഭ്യമല്ല.",
            show_alert=True
        )
        return

    if action == "reject":

        request["status"] = "rejected"

        await query.message.edit_text(
            query.message.text + "\n\n❌ **Request Rejected**",
            reply_markup=None
        )

        await query.answer("Rejected")
        return

    request["status"] = "accepted"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "DB1",
                callback_data=f"idx_db:db1:{request_id}"
            ),
            InlineKeyboardButton(
                "DB2",
                callback_data=f"idx_db:db2:{request_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "DB3",
                callback_data=f"idx_db:db3:{request_id}"
            ),
            InlineKeyboardButton(
                "ALL DATABASES",
                callback_data=f"idx_db:all:{request_id}"
            )
        ]
    ])

    await query.message.edit_text(
        query.message.text
        + "\n\n✅ Request Accepted"
        + "\n🗄️ Database തിരഞ്ഞെടുക്കുക:",
        reply_markup=buttons
    )

    await query.answer("Select Database")


# ----------------------------------
# DATABASE SELECTION
# ----------------------------------

@Client.on_callback_query(
    filters.regex(r"^idx_db:(db1|db2|db3|all):")
)
async def select_index_database(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:
        await query.answer(
            "⛔ നിങ്ങൾക്ക് അനുമതിയില്ല!",
            show_alert=True
        )
        return

    _, database, request_id = query.data.split(":", 2)

    request = index_requests.get(request_id)

    if not request or request["status"] != "accepted":
        await query.answer(
            "❌ Request ലഭ്യമല്ല.",
            show_alert=True
        )
        return

    # Check database availability
    collections = get_target_collections(database)

    if not collections:
        await query.answer(
            f"❌ {database.upper()} Database ലഭ്യമല്ല!",
            show_alert=True
        )
        return

    request["database"] = database
    request["status"] = "indexing"
    request["cancelled"] = False

    await query.answer("Indexing Started")

    cancel_button = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛑 CANCEL INDEXING",
                callback_data=f"idx_cancel:{request_id}"
            )
        ]
    ])

    await query.message.edit_text(
        query.message.text
        + "\n\n⏳ **Indexing Started**"
        + f"\n🗄️ Database: `{database.upper()}`"
        + "\n📁 Indexed: `0`"
        + "\n⏭️ Skipped: `0`",
        reply_markup=cancel_button
    )

    indexed = 0
    skipped = 0
    checked = 0

    try:

        channel = request["channel"]

        # Normalize public Telegram links
        if channel.startswith("https://t.me/"):
            channel = channel.replace(
                "https://t.me/", ""
            ).strip("/")

        elif channel.startswith("http://t.me/"):
            channel = channel.replace(
                "http://t.me/", ""
            ).strip("/")

        if channel.startswith("@"):
            channel = channel[1:]

        # Public channel lookup
        chat = await client.get_chat(channel)

        media_types = [
            "document",
            "video",
            "audio",
            "animation",
            "photo",
            "voice",
            "video_note"
        ]

        async for msg in client.get_chat_history(chat.id):

            # CANCEL CHECK
            if request.get("cancelled"):

                request["status"] = "cancelled"

                await query.message.edit_text(
                    query.message.text
                    + "\n\n🛑 **Indexing Cancelled**"
                    + f"\n📁 Indexed: `{indexed}`"
                    + f"\n⏭️ Skipped: `{skipped}`",
                    reply_markup=None
                )

                return

            checked += 1

            media = None
            media_type = None

            for item in media_types:

                value = getattr(msg, item, None)

                if value:
                    media = value
                    media_type = item
                    break

            if not media:
                continue

            file_name = getattr(media, "file_name", None)

            caption = msg.caption or ""

            # Episode filter checks both filename and caption
            episode_text = f"{file_name or ''} {caption}"

            if is_tv_episode(episode_text):

                skipped += 1
                continue

            file_data = {
                "file_id": media.file_id,
                "file_unique_id": media.file_unique_id,
                "file_name": file_name,
                "file_size": getattr(media, "file_size", 0),
                "mime_type": getattr(media, "mime_type", None),
                "file_type": media_type,
                "caption": caption,
                "chat_id": msg.chat.id,
                "message_id": msg.id,
                "date": msg.date
            }

            saved = await save_file_to_databases(
                file_data,
                target=database
            )

            if saved:
                indexed += 1

            # LIVE PROGRESS UPDATE
            if checked % 100 == 0:

                await query.message.edit_text(
                    f"⏳ **Indexing In Progress**"
                    f"\n\n🔗 Channel: `{chat.title}`"
                    f"\n🗄️ Database: `{database.upper()}`"
                    f"\n📁 Indexed: `{indexed}`"
                    f"\n⏭️ Skipped: `{skipped}`"
                    f"\n🔍 Checked: `{checked}`",
                    reply_markup=cancel_button
                )

        request["status"] = "completed"

        await query.message.edit_text(
            f"✅ **Indexing Completed**"
            f"\n\n🔗 Channel: `{chat.title}`"
            f"\n🗄️ Database: `{database.upper()}`"
            f"\n📁 Indexed: `{indexed}`"
            f"\n⏭️ TV Episodes Skipped: `{skipped}`"
            f"\n🔍 Messages Checked: `{checked}`",
            reply_markup=None
        )

    except Exception as e:

        request["status"] = "failed"

        print(f"Indexing Error: {e}")

        await query.message.edit_text(
            f"❌ **Indexing Failed**"
            f"\n\nError: `{str(e)[:500]}`"
            f"\n📁 Indexed: `{indexed}`"
            f"\n⏭️ Skipped: `{skipped}`",
            reply_markup=None
        )


# ----------------------------------
# CANCEL INDEXING
# ----------------------------------

@Client.on_callback_query(
    filters.regex(r"^idx_cancel:")
)
async def cancel_indexing(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:
        await query.answer(
            "⛔ Access Denied",
            show_alert=True
        )
        return

    request_id = query.data.split(":", 1)[1]

    request = index_requests.get(request_id)

    if not request or request["status"] != "indexing":

        await query.answer(
            "Indexing ഇപ്പോൾ പ്രവർത്തിക്കുന്നില്ല.",
            show_alert=True
        )
        return

    request["cancelled"] = True

    await query.answer(
        "🛑 Cancel Request Sent"
    )
