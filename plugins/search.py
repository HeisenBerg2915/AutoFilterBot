import re
import difflib
from datetime import datetime
from uuid import uuid4
from urllib.parse import quote_plus

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    files_col,
    files_col2,
    files_col3,
    stats_col,
    search_sessions_col
)

PAGE_SIZE = 8

# Available databases
DATABASES = [
    (files_col, "1"),
    (files_col2, "2"),
    (files_col3, "3")
]


def build_search_filter(query):

    words = re.findall(r"[^\W_]+", query, flags=re.UNICODE)

    if not words:
        return None

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

    for file, db_number in results:

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

        document_id = str(file["_id"])

        payload = f"f{db_number}_{document_id}"

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


async def get_search_results(search_filter, limit):

    all_results = []

    for collection, db_number in DATABASES:

        if collection is None:
            continue

        results = await collection.find(
            search_filter
        ).sort(
            "date", -1
        ).limit(
            limit
        ).to_list(length=limit)

        for file in results:
            all_results.append((file, db_number))

    all_results.sort(
        key=lambda item: item[0].get("date") or datetime.min,
        reverse=True
    )

    return all_results


async def show_page(client, message, query, session_id, page):

    search_filter = build_search_filter(query)

    if not search_filter:
        return

    total = 0

    for collection, _ in DATABASES:

        if collection is not None:
            total += await collection.count_documents(search_filter)

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    page = max(0, min(page, total_pages - 1))

    limit = (page + 1) * PAGE_SIZE

    all_results = await get_search_results(
        search_filter,
        limit
    )

    results = all_results[
        page * PAGE_SIZE:(page + 1) * PAGE_SIZE
    ]

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


# =========================
# SPELLING CHECK FEATURE
# =========================

async def get_spelling_suggestions(query, limit=5):

    candidates = set()

    for collection, _ in DATABASES:

        if collection is None:
            continue

        try:
            names = await collection.distinct("file_name")

            for name in names:

                if not name:
                    continue

                clean = re.sub(
                    r"\.[a-zA-Z0-9]{2,5}$",
                    "",
                    str(name)
                )

                clean = re.sub(
                    r"\b(480p|720p|1080p|2160p|4k|hd|web[- ]?dl|bluray|"
                    r"x264|x265|hevc|h264|h265)\b",
                    " ",
                    clean,
                    flags=re.IGNORECASE
                )

                clean = re.sub(
                    r"[\W_]+",
                    " ",
                    clean
                ).strip()

                if clean:
                    candidates.add(clean)

        except Exception as error:
            print(f"Spelling suggestion error: {error}")

    if not candidates:
        return []

    normalized = {
        name.casefold(): name
        for name in candidates
    }

    matches = difflib.get_close_matches(
        query.casefold(),
        list(normalized.keys()),
        n=limit,
        cutoff=0.48
    )

    return [
        normalized[item]
        for item in matches
    ]


async def show_spelling_check(client, message, query):

    suggestions = await get_spelling_suggestions(query)

    session_id = uuid4().hex

    await search_sessions_col.insert_one({
        "_id": session_id,
        "query": query,
        "suggestions": suggestions,
        "chat_id": message.chat.id,
        "created_at": datetime.utcnow()
    })

    buttons = []

    for index, suggestion in enumerate(suggestions):

        buttons.append([
            InlineKeyboardButton(
                f"🔎 {suggestion[:50]}",
                callback_data=f"sp:{session_id}:{index}"
            )
        ])

    google_query = quote_plus(query)

    buttons.append([
        InlineKeyboardButton(
            "🌐 Check Spelling (Google)",
            url=f"https://www.google.com/search?q={google_query}"
        )
    ])

    text = (
        "🚫 **No exact files found!**\n\n"
        "🔤 **Spelling Check**\n"
        "താഴെ കാണുന്ന പേരുകളിൽ ഉദ്ദേശിച്ച സിനിമ ഉണ്ടോ എന്ന് പരിശോധിക്കുക. "
        "ശരിയായ പേര് തിരഞ്ഞെടുക്കുമ്പോൾ വീണ്ടും search ചെയ്യും."
    )

    if not suggestions:

        text += (
            "\n\n💡 ഈ പേരിനോട് സാമ്യമുള്ള indexed file "
            "കണ്ടെത്താനായില്ല."
        )

    else:

        text += "\n\n👇 **Did you mean?**"

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        reply_to_message_id=message.id,
        disable_web_page_preview=True
    )


# =========================
# AUTO FILTER
# =========================

@Client.on_message(filters.group & filters.text)
async def auto_filter(client, message):

    query = message.text.strip()

    if query.startswith("/") or len(query) < 2:
        return

    search_filter = build_search_filter(query)

    if not search_filter:
        return

    total = 0

    for collection, _ in DATABASES:

        if collection is not None:
            total += await collection.count_documents(search_filter)

    if not total:

        await show_spelling_check(
            client,
            message,
            query
        )

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

    total_pages = max(
        1,
        (total + PAGE_SIZE - 1) // PAGE_SIZE
    )

    results = await get_search_results(
        search_filter,
        PAGE_SIZE
    )

    results = results[:PAGE_SIZE]

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


# =========================
# PAGINATION CALLBACK
# =========================

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


# =========================
# SPELLING SUGGESTION CALLBACK
# =========================

@Client.on_callback_query(filters.regex(r"^sp:"))
async def spelling_suggestion_callback(client, callback_query):

    try:

        _, session_id, index = callback_query.data.split(":")
        index = int(index)

    except (ValueError, AttributeError):

        await callback_query.answer(
            "Invalid suggestion!",
            show_alert=True
        )

        return

    session = await search_sessions_col.find_one({
        "_id": session_id
    })

    if not session or callback_query.message.chat.id != session.get("chat_id"):

        await callback_query.answer(
            "⌛ Suggestion expired. Please search again.",
            show_alert=True
        )

        return

    suggestions = session.get("suggestions", [])

    if index < 0 or index >= len(suggestions):

        await callback_query.answer(
            "Suggestion not found!",
            show_alert=True
        )

        return

    selected_query = suggestions[index]

    await search_sessions_col.update_one(
        {"_id": session_id},
        {"$set": {"query": selected_query}}
    )

    await callback_query.answer(
        f"Searching: {selected_query}"
    )

    await show_page(
        client,
        callback_query.message,
        selected_query,
        session_id,
        0
    )
