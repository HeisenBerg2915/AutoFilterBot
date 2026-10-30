import re

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import app
from database import files_col, stats_col
from config import MAX_RESULTS


@app.on_message(filters.group & filters.text & ~filters.command)
async def auto_filter(client, message):

    query = message.text.strip()

    if len(query) < 2:
        return

    # Search MongoDB
    pattern = re.escape(query)

    results = await files_col.find({
        "$or": [
            {"file_name": {"$regex": pattern, "$options": "i"}},
            {"caption": {"$regex": pattern, "$options": "i"}}
        ]
    }).limit(MAX_RESULTS).to_list(length=MAX_RESULTS)

    if not results:
        return

    # Update Search Counter
    await stats_col.update_one(
        {"_id": "bot_stats"},
        {"$inc": {"searches": 1}},
        upsert=True
    )

    me = await client.get_me()

    buttons = []

    for file in results:

        file_name = (
            file.get("file_name")
            or file.get("caption")
            or "Unknown File"
        )

        chat_id = file.get("chat_id")
        message_id = file.get("message_id")

        payload = f"file_{chat_id}_{message_id}"

        button = InlineKeyboardButton(
            text=f"📁 {file_name[:35]}",
            url=f"https://t.me/{me.username}?start={payload}"
        )

        buttons.append([button])

    await message.reply_text(
        f"🔎 Search Results: {query}\n\n"
        f"📁 Found {len(results)} Files",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
