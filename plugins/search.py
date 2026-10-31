import re
from datetime import datetime
from uuid import uuid4

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import files_col, stats_col, search_sessions_col

PAGE_SIZE = 8


def build_search_filter(query):
    """
    Match complete words while ignoring differences
    between spaces, dots, hyphens and underscores.
    """

    words = re.findall(r"[^\W_]+", query, flags=re.UNICODE)

    if not words:
        return None

    # Allow punctuation or spaces between search words
    pattern = r"(^|[\W_])" + r"[\W_]+".join(
        re.escape(word) for word in words
    ) + r"($|[\W_])"

    return {
        "$or": [
            {
                "file_name": {
                    "$regex": pattern,
                    "$options": "i"
                }
            },
            {
                "caption": {
                    "$regex": pattern,
                    "$options": "i"
                }
            }
        ]
    }


def get_file_buttons(client, results, session_id, page, total_pages):

    buttons = []

    for file in results:

        file_name = (
            file.get("file_name")
            or file.get("caption")
            or "Unknown File"
        )

        file_size = file.get("file_size", 0) or 0
        size_mb = file_size / (1024 * 1024)

        if size_mb >= 1024:
            size_text = f"{size_mb / 1024:.2f}GB"
        else:
            size_text = f"{size_mb:.0f}MB"

        # Use MongoDB document ID for a short Telegram deep link
        document_id = str(file["_id"])

        payload = f"f_{document_id}"

        buttons.append([
            InlineKeyboardButton(
                text=f"{size_text} ➠ {file_name[:45]}",
                url=f"https://t.me/{client.me.username}?start={payload}"
            )
        ])

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"pg:{session_id}:{page - 1}"
            )
        )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"pg:{session_id}:{page + 1}"
            )
        )

    if navigation:
        buttons.append(navigation)

    return InlineKeyboardMarkup(buttons)


async def show_page(client, message, query, session_id, page):

    search_filter = build_search_filter(query)

    if not search_filter:
        return

    total = await files_col.count_documents(search_filter)

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    page = max(0, min(page, total_pages - 1))

    results = await files_col.find(
        search_filter
    ).skip(
        page * PAGE_SIZE
    ).limit(
        PAGE_SIZE
    ).to_list(length=PAGE_SIZE)

    keyboard = get_file_buttons(
        client,
        results,
        session_id,
        page,
        total_pages
    )

    await message.edit_text(
        f"🔎 Search Results: {query}\n\n"
        f"📁 Found: {total} Files\n"
        f"📄 Page: {page + 1}/{total_pages}",
        reply_markup=keyboard
    )


@Client.on_message(filters.group & filters.text)
async def auto_filter(client, message):

    query = message.text.strip()

    if query.startswith("/") or len(query) < 2:
        return

    search_filter = build_search_filter(query)

    if not search_filter:
        return

    total = await files_col.count_documents(search_filter)

    if not total:
        return

    await stats_col.update_one(
        {"_id": "bot_stats"},
        {"$inc": {"searches": 1}},
        upsert=True
    )

    session_id = uuid4().hex

    await search_sessions_col.insert_one({
        "_id": session_id,
        "query": query,
        "chat_id": message.chat.id,
        "created_at": datetime.utcnow()
    })

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    results = await files_col.find(
        search_filter
    ).limit(
        PAGE_SIZE
    ).to_list(length=PAGE_SIZE)

    keyboard = get_file_buttons(
        client,
        results,
        session_id,
        0,
        total_pages
    )

    await message.reply_text(
        f"🔎 Search Results: {query}\n\n"
        f"📁 Found: {total} Files\n"
        f"📄 Page: 1/{total_pages}",
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex(r"^pg:"))
async def pagination_callback(client, callback_query):

    try:
        _, session_id, page = callback_query.data.split(":")
        page = int(page)

    except (ValueError, AttributeError):
        await callback_query.answer(
            "Invalid Page!",
            show_alert=True
        )
        return

    session = await search_sessions_col.find_one({
        "_id": session_id
    })

    if not session:
        await callback_query.answer(
            "⌛ Pagination expired! Please search again.",
            show_alert=True
        )
        return

    if callback_query.message.chat.id != session["chat_id"]:
        await callback_query.answer(
            "Invalid Session!",
            show_alert=True
        )
        return

    await callback_query.answer()

    await show_page(
        client,
        callback_query.message,
        session["query"],
        session_id,
        page
    )
