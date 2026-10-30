import re

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import app
from database import files_col
from config import BOT_USERNAME, MAX_RESULTS


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

    buttons = []

    for file in results:

        file_name = (
            file.get("file_name")
            or file.get("caption")
            or "Unknown File"
        )

        message_id = file.get("message_id")

        button = InlineKeyboardButton(
            text=f"📁 {file_name[:40]}",
            url=f"https://t.me/{BOT_USERNAME}?start=file_{message_id}"
        )

        buttons.append([button])

    await message.reply_text(
        f"🔎 Search Results: {query}\n\n"
        f"📁 Found {len(results)} Files",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
