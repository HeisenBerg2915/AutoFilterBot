from uuid import uuid4

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL, ADMINS
from helpers.database_router import save_file_to_databases
from helpers.episode_filter import is_tv_episode


index_requests = {}


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
        "database": None
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
            query.message.text + "\n\n❌ Request Rejected",
            reply_markup=None
        )

        await query.answer("Rejected")
        return

    request["status"] = "accepted"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("DB1", callback_data=f"idx_db:db1:{request_id}"),
            InlineKeyboardButton("DB2", callback_data=f"idx_db:db2:{request_id}")
        ],
        [
            InlineKeyboardButton("DB3", callback_data=f"idx_db:db3:{request_id}"),
            InlineKeyboardButton("ALL DATABASES", callback_data=f"idx_db:all:{request_id}")
        ]
    ])

    await query.message.edit_text(
        query.message.text + "\n\n✅ Request Accepted\n🗄️ Database തിരഞ്ഞെടുക്കുക:",
        reply_markup=buttons
    )

    await query.answer("Select Database")


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

    request["database"] = database
    request["status"] = "indexing"
    request["cancelled"] = False

    await query.answer("Indexing Started")

    await query.message.edit_text(
        query.message.text + "\n\n⏳ Indexing ആരംഭിക്കുന്നു..."
    )

    try:
        channel = request["channel"]

        if channel.startswith("https://t.me/"):
            channel = channel.replace("https://t.me/", "").strip("/")
        
        if channel.startswith("@"):
            channel = channel[1:]

        chat = await client.get_chat(channel)

        indexed = 0
        skipped = 0

        async for msg in client.get_chat_history(chat.id):

            media_types = [
                "document",
                "video",
                "audio",
                "animation",
                "photo",
                "voice",
                "video_note"
            ]

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

            if is_tv_episode(file_name or caption):
                skipped += 1
                continue

            file_data = {
                "file_id": media.file_id,
                "file_unique_id": media.file_unique_id,
                "file_name": file_name,
                "file_size": media.file_size,
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

        request["status"] = "completed"

        await query.message.edit_text(
            query.message.text
            + f"\n\n✅ **Indexing Completed**"
            + f"\n📁 Indexed: `{indexed}`"
            + f"\n⏭️ TV Episodes Skipped: `{skipped}`"
            + f"\n🗄️ Database: `{database.upper()}`"
        )

    except Exception as e:

        request["status"] = "failed"

        print(f"Indexing Error: {e}")

        await query.message.edit_text(
            query.message.text
            + f"\n\n❌ **Indexing Failed**"
            + f"\nError: `{str(e)[:500]}`"
        )
