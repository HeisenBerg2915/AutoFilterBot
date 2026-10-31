import re
import os
import asyncio
import logging

from datetime import datetime
from uuid import uuid4
from urllib.parse import quote_plus

import aiohttp

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# DATABASE IMPORTS
# =========================

from database import (
    files_col,
    files_col2,
    files_col3,
    stats_col,
    search_sessions_col
)

# =========================
# SETTINGS
# =========================

PAGE_SIZE = 8

logger = logging.getLogger(__name__)

# =========================
# IMDbio IMPORT
# =========================

try:
    import imdbio
    IMDBIO_AVAILABLE = True
except ImportError:
    imdbio = None
    IMDBIO_AVAILABLE = False


# =========================
# DATABASES
# =========================

DATABASES = [
    (files_col, "1"),
    (files_col2, "2"),
    (files_col3, "3")
]


# =========================
# OMDB API KEY ROTATION
# =========================

OMDB_KEY_INDEX = 0
OMDB_KEY_LOCK = asyncio.Lock()


def get_omdb_api_keys():

    raw = (
        os.getenv("OMDB_API_KEYS", "")
        or os.getenv("OMDB_API_KEY", "")
    )

    return [
        key.strip()
        for key in raw.replace(";", ",").split(",")
        if key.strip()
    ]


async def get_next_omdb_key():

    global OMDB_KEY_INDEX

    keys = get_omdb_api_keys()

    if not keys:
        return None

    async with OMDB_KEY_LOCK:

        key = keys[OMDB_KEY_INDEX % len(keys)]

        OMDB_KEY_INDEX = (
            OMDB_KEY_INDEX + 1
        ) % len(keys)

        return key


# =========================
# CLEAN SPELLING QUERY
# =========================

def clean_spelling_query(raw_query):

    cleaned = re.sub(
        r"\b(pl(i|e)\*?(s|z+|ease|se|ese|(e+)s(e)?)|"
        r"((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|"
        r"br((o|u)h?)\*|mal(ayalam)?|t(h)?amil|file|that|find|"
        r"full\smovie|any(one)|with\ssubtitle(s)?)",
        "",
        raw_query,
        flags=re.IGNORECASE
    ).strip()

    return cleaned or raw_query.strip()


# =========================
# IMDbio SEARCH
# =========================

async def get_imdbio_suggestions(query, limit=6):

    if not IMDBIO_AVAILABLE:
        return []

    year_match = re.search(
        r"\b(19\d{2}|20\d{2})\b",
        query
    )

    year = (
        year_match.group(1)
        if year_match else None
    )

    title = query

    if year:
        title = re.sub(
            r"\b(19\d{2}|20\d{2})\b",
            "",
            query
        ).strip()

    try:

        result = await asyncio.to_thread(
            imdbio.search_title,
            title,
            year=year
        )

        if not result or not result.titles:
            return []

        suggestions = []

        for movie in result.titles[:limit]:

            movie_title = getattr(
                movie,
                "title",
                None
            )

            movie_year = getattr(
                movie,
                "year",
                None
            )

            if not movie_title:
                continue

            suggestions.append({
                "title": str(movie_title),
                "year": (
                    str(movie_year)
                    if movie_year else "N/A"
                )
            })

        return suggestions

    except Exception as error:

        logger.warning(
            "IMDbio search error: %s",
            error
        )

        return []


# =========================
# OMDB SEARCH
# =========================

async def get_omdb_suggestions(query, limit=6):

    keys = get_omdb_api_keys()

    if not keys:
        return []

    year_match = re.search(
        r"\b(19\d{2}|20\d{2})\b",
        query
    )

    year = (
        year_match.group(1)
        if year_match else None
    )

    title = query

    if year:
        title = re.sub(
            r"\b(19\d{2}|20\d{2})\b",
            "",
            query
        ).strip()

    timeout = aiohttp.ClientTimeout(total=12)

    # Try each configured key.
    for _ in range(len(keys)):

        api_key = await get_next_omdb_key()

        if not api_key:
            break

        try:

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.get(
                    "https://www.omdbapi.com/",
                    params={
                        "apikey": api_key,
                        "s": title,
                        **(
                            {"y": year}
                            if year else {}
                        )
                    }
                ) as response:

                    if response.status != 200:

                        logger.warning(
                            "OMDb HTTP error: %s",
                            response.status
                        )

                        continue

                    data = await response.json(
                        content_type=None
                    )

            if data.get("Response") == "True":

                results = data.get("Search", [])

                return [
                    {
                        "title": item.get("Title"),
                        "year": item.get("Year") or "N/A"
                    }
                    for item in results[:limit]
                    if item.get("Title")
                ]

            error = str(
                data.get("Error", "")
            )

            logger.warning(
                "OMDb API response: %s",
                error
            )

            error_lower = error.lower()

            # Search result not found is not a key error.
            if "not found" in error_lower:
                return []

            # Try next key for quota/authentication errors.
            if (
                "limit" in error_lower
                or "invalid api key" in error_lower
                or "disabled" in error_lower
            ):
                continue

            return []

        except asyncio.CancelledError:
            raise

        except Exception as error:

            logger.warning(
                "OMDb request error: %s",
                error
            )

            continue

    return []


# =========================
# MOVIE SUGGESTIONS
# =========================

async def get_movie_suggestions(query, limit=6):

    # First: IMDbio

    movies = await get_imdbio_suggestions(
        query,
        limit
    )

    if movies:
        return movies[:limit]

    # Second: OMDb fallback

    movies = await get_omdb_suggestions(
        query,
        limit
    )

    return movies[:limit]


# =========================
# SPELLING CHECK MESSAGE
# =========================

async def show_spelling_check(message, raw_query):

    cleaned_query = clean_spelling_query(
        raw_query
    )

    try:

        movies = await get_movie_suggestions(
            cleaned_query,
            limit=6
        )

    except Exception as error:

        logger.exception(
            "Spelling check error: %s",
            error
        )

        movies = []

    google_url = (
        "https://www.google.com/search?q="
        + quote_plus(raw_query)
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔎 ᴄʜᴇᴄᴋ sᴘᴇʟʟ (ɢᴏᴏɢʟᴇ) 🔎",
                url=google_url
            )
        ]
    ])

    text = (
        "<blockquote>"
        "<b>🚫 ᴏᴛᴛ ɴ/ᴀ ➪ ᴄʜᴇᴄᴋ sᴘᴇʟʟ 🚫</b>\n\n"
        "───────────────\n"
        "<b>➳ ᴛʜᴇ ᴍᴏᴠɪᴇ ʜᴀs ɴᴏᴛ ʙᴇᴇɴ ғᴏᴜɴᴅ ɪɴ ᴏᴜʀ ғɪʟᴇs.</b>\n"
        "<b>➳ ɪғ ɪᴛ ʜᴀs ʙᴇᴇɴ ʀᴇʟᴇᴀsᴇᴅ, ᴘʟᴇᴀsᴇ ᴛʀʏ sᴇᴀʀᴄʜɪɴɢ ᴀɢᴀɪɴ ᴜsɪɴɢ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ sᴘᴇʟʟɪɴɢ ᴘʀᴏᴠɪᴅᴇᴅ ʙᴇʟᴏᴡ.</b>\n"
        "<b>➳ ɪғ ʏᴏᴜ sᴛɪʟʟ ᴄᴀɴɴᴏᴛ ғɪɴᴅ ɪᴛ, ᴘʟᴇᴀsᴇ ᴜsᴇ ᴛʜᴇ ɢᴏᴏɢʟᴇ ʙᴜᴛᴛᴏɴ.</b>"
        "</blockquote>"
    )

    seen = set()
    movie_list = []

    for movie in movies:

        title = str(
            movie.get("title") or ""
        ).strip()

        year = str(
            movie.get("year") or "N/A"
        )

        if not title:
            continue

        year_match = re.search(
            r"\b(19\d{2}|20\d{2})\b",
            year
        )

        year_text = (
            f" {year_match.group(1)}"
            if year_match else ""
        )

        movie_name = title + year_text

        if movie_name.casefold() in seen:
            continue

        seen.add(movie_name.casefold())

        movie_list.append(movie_name)

        if len(movie_list) >= limit:
            break

    if movie_list:

        text += (
            "\n───────────────\n"
            "💡 <b>sᴜɢɢᴇsᴛɪᴏɴs</b>\n\n"
        )

        for index, movie_name in enumerate(
            movie_list,
            start=1
        ):

            safe_name = (
                movie_name
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            text += (
                f"<b>{index}.</b> "
                f"<code>{safe_name}</code>\n"
            )

    else:

        text += (
            "\n━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>sᴜɢɢᴇsᴛɪᴏɴs</b>\n"
            "<i>No suggestions available right now.</i>\n"
        )

    await message.reply_text(
        text=text,
        reply_markup=keyboard,
        reply_to_message_id=message.id,
        parse_mode="html",
        disable_web_page_preview=True
    )


# =========================
# BUILD SEARCH FILTER
# =========================

def build_search_filter(query):

    words = re.findall(
        r"[^\W_]+",
        query,
        flags=re.UNICODE
    )

    if not words:
        return None

    pattern = (
        r"(^|[\W_])"
        + r"[\W_]+".join(
            re.escape(word)
            for word in words
        )
        + r"($|[\W_])"
    )

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


# =========================
# FILE BUTTONS
# =========================

def get_file_buttons(
    client,
    results,
    session_id,
    page,
    total_pages
):

    buttons = []

    for file, db_number in results:

        file_name = (
            file.get("file_name")
            or file.get("caption")
            or "Unknown File"
        )

        file_size = file.get(
            "file_size",
            0
        ) or 0

        size_mb = file_size / (
            1024 * 1024
        )

        if size_mb >= 1024:

            size_text = (
                f"{size_mb / 1024:.2f}GB"
            )

        else:

            size_text = (
                f"{size_mb:.0f}MB"
            )

        document_id = str(
            file["_id"]
        )

        payload = (
            f"f{db_number}_{document_id}"
        )

        buttons.append([
            InlineKeyboardButton(
                text=(
                    f"{size_text} ➠ "
                    f"{file_name[:45]}"
                ),
                url=(
                    f"https://t.me/"
                    f"{client.me.username}"
                    f"?start={payload}"
                )
            )
        ])

    navigation = []

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=(
                    f"pg:{session_id}:{page - 1}"
                )
            )
        )

    if page < total_pages - 1:

        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=(
                    f"pg:{session_id}:{page + 1}"
                )
            )
        )

    if navigation:
        buttons.append(navigation)

    return InlineKeyboardMarkup(buttons)


# =========================
# GET SEARCH RESULTS
# =========================

async def get_search_results(
    search_filter,
    limit
):

    all_results = []

    for collection, db_number in DATABASES:

        if collection is None:
            continue

        results = await collection.find(
            search_filter
        ).sort(
            "date",
            -1
        ).limit(
            limit
        ).to_list(
            length=limit
        )

        for file in results:

            all_results.append(
                (file, db_number)
            )

    all_results.sort(
        key=lambda item: (
            item[0].get("date")
            or datetime.min
        ),
        reverse=True
    )

    return all_results


# =========================
# SHOW PAGINATION PAGE
# =========================

async def show_page(
    client,
    message,
    query,
    session_id,
    page
):

    search_filter = build_search_filter(
        query
    )

    if not search_filter:
        return

    total = 0

    for collection, _ in DATABASES:

        if collection is not None:

            total += await collection.count_documents(
                search_filter
            )

    total_pages = max(
        1,
        (total + PAGE_SIZE - 1) // PAGE_SIZE
    )

    page = max(
        0,
        min(page, total_pages - 1)
    )

    limit = (
        (page + 1) * PAGE_SIZE
    )

    all_results = await get_search_results(
        search_filter,
        limit
    )

    results = all_results[
        page * PAGE_SIZE:
        (page + 1) * PAGE_SIZE
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
# AUTO FILTER
# =========================

@Client.on_message(
    filters.group & filters.text
)
async def auto_filter(
    client,
    message
):

    query = message.text.strip()

    if query.startswith("/") or len(query) < 2:
        return

    search_filter = build_search_filter(
        query
    )

    if not search_filter:
        return

    total = 0

    for collection, _ in DATABASES:

        if collection is not None:

            total += await collection.count_documents(
                search_filter
            )

    # SPELLING CHECK
    if not total:

        try:

            await show_spelling_check(
                message,
                query
            )

        except Exception as error:

            logger.exception(
                "Spelling check error: %s",
                error
            )

        return

    # SEARCH STATS
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

@Client.on_callback_query(
    filters.regex(r"^pg:")
)
async def pagination_callback(
    client,
    callback_query
):

    try:

        _, session_id, page = (
            callback_query.data.split(":")
        )

        page = int(page)

    except (
        ValueError,
        AttributeError
    ):

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

    if (
        callback_query.message.chat.id
        != session["chat_id"]
    ):

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
