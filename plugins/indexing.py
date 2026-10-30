from uuid import uuid4

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL, ADMINS


@Client.on_message(filters.command("index") & filters.private)
async def index_request(client, message):

    if len(message.command) < 2:
        await message.reply_text(
            "⚠️ ഉപയോഗം:\n/index @channelusername"
        )
        return

    if not LOG_CHANNEL:
        await message.reply_text(
            "❌ Moderator Log Channel configure ചെയ്തിട്ടില്ല."
        )
        return

    channel_link = message.text.split(maxsplit=1)[1].strip()
    request_id = uuid4().hex[:10]
    user = message.from_user

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
            f"👤 User: {user.mention}\n"
            f"🆔 User ID: `{user.id}`\n"
            f"🔗 Channel: `{channel_link}`\n"
            f"📝 Request ID: `{request_id}`",
            reply_markup=buttons
        )

        await message.reply_text(
            "✅ Indexing Request Moderator-ന് അയച്ചു."
        )

    except Exception as e:
        print(f"Index Request Error: {e}")
        await message.reply_text("❌ Request അയക്കാൻ കഴിഞ്ഞില്ല.")


@Client.on_callback_query(filters.regex(r"^idx_(accept|reject):"))
async def indexing_approval(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:
        await query.answer(
            "⛔ നിങ്ങൾക്ക് അനുമതിയില്ല!",
            show_alert=True
        )
        return

    action, request_id = query.data.split(":", 1)

    if action == "accept":

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
            + "\n\n✅ **Request Accepted**\n\n"
            "🗄️ ഏത് Database-ലേക്ക് Index ചെയ്യണം?",
            reply_markup=buttons
        )

        await query.answer("Select Database")

    else:

        await query.message.edit_text(
            query.message.text
            + "\n\n❌ **Request Rejected**",
            reply_markup=None
        )

        await query.answer("Request Rejected")
