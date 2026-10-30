from uuid import uuid4

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL, ADMINS

# Temporary request storage
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
            "✅ Request Moderator-ന് അയച്ചു."
        )

    except Exception as e:
        index_requests.pop(request_id, None)
        print(f"Index Request Error: {e}")

        await message.reply_text(
            "❌ Request അയക്കാൻ കഴിഞ്ഞില്ല."
        )


@Client.on_callback_query(
    filters.regex(r"^idx_(accept|reject):")
)
async def indexing_approval(client, query):

    if query.from_user.id not in ADMINS:
        await query.answer(
            "⛔ നിങ്ങൾക്ക് അനുമതിയില്ല!",
            show_alert=True
        )
        return

    action, request_id = query.data.split(":", 1)

    request = index_requests.get(request_id)

    if not request:
        await query.answer(
            "❌ Request ലഭ്യമല്ല. വീണ്ടും അയക്കുക.",
            show_alert=True
        )
        return

    if request["status"] != "pending":
        await query.answer(
            "ഈ Request ഇതിനകം പരിശോധിച്ചിട്ടുണ്ട്.",
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
        + "\n\n✅ **Request Accepted**\n"
        "🗄️ Database തിരഞ്ഞെടുക്കുക:",
        reply_markup=buttons
    )

    await query.answer("Select Database")


@Client.on_callback_query(
    filters.regex(r"^idx_db:(db1|db2|db3|all):")
)
async def select_index_database(client, query):

    if query.from_user.id not in ADMINS:
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
    request["status"] = "database_selected"

    await query.message.edit_text(
        query.message.text
        + f"\n\n🗄️ **Selected Database:** `{database.upper()}`\n"
        "⏳ അടുത്ത ഘട്ടത്തിൽ Indexing ആരംഭിക്കാം.",
        reply_markup=None
    )

    await query.answer(
        f"{database.upper()} Selected"
    )
