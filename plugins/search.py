import re

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import files_col, stats_col
from config import MAX_RESULTS


@Client.on_message(filters.group & filters.text)
async def auto_filter(client, message):

    query = message.text.strip()

    if query.startswith("/"):
        return

    if len(query) < 2:
        return

    pattern = re.escape(query)

    results = await files_col.find({
        "$or": [
            {"file_name": {"$regex": pattern, "$options": "i"}},
            {"caption": {"$regex": pattern, "$options": "i"}}
        ]
    }).limit(MAX_RESULTS).to_list(length=MAX_RESULTS)

    if not results:
        return

    await stats_col.update_one(
        {"_id": "bot_stats"},
        {"$inc": {"searches": 1}},
        upsert=True
    )

    buttons = []

    for file in results:

        file_name = (
            file.get("file_name")
            or file.get("caption")
            or "Unknown File"
        )

        file_size = file.get("file_size", 0)

        size_mb = file_size / (1024 * 1024)

        if size_mb >= 1024:
            size_text = f"{size_mb / 1024:.2f}GB"
        else:
            size_text = f"{size_mb:.0f}MB"

        chat_id = file.get("chat_id")
        message_id = file.get("message_id")

        buttons.append([
            InlineKeyboardButton(
                text=f"{size_text} ➠ {file_name}",
                url=f"https://t.me/c/{str(chat_id)[4:]}/{message_id}"
            )
        ])

    await message.reply_text(
        f"🔎 Search Results: {query}\n\n"
        f"📁 Found {len(results)} Files",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
