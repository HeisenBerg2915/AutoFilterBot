import re
import asyncio

from html import escape
from urllib.parse import quote_plus

from datetime import datetime
from uuid import uuid4

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    files_col,
    files_col2,
    files_col3,
    stats_col,
    search_sessions_col,
    missing_col,
    notify_requests_col,
    groups_col
)

from config import UPDATE_GROUP

import imdbio

from tag_cleaner import clean_file_name

PAGE_SIZE = 8


# =========================
# AVAILABLE DATABASES
# =========================

DATABASES = [
    (files_col, "1"),
    (files_col2, "2"),
    (files_col3, "3")
]


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
            re.escape(word) for word in words
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

        original_name = (
            file.get("file_name")
            or file.get("caption")
            or "Unknown File"
        )

        file_name = clean_file_name(original_name)

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


# =========================
# GET SEARCH RESULTS
# =========================

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


# =========================
# SHOW SEARCH PAGE
# =========================

async def show_page(
    client,
    message,
    query,
    session_id,
    page
):

    search_filter = build_search_filter(query)

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
# IMDbIO MOVIE SUGGESTIONS
# =========================

async def get_movie_suggestions(query, bulk=False):

    if not query:
        return None

    query = query.strip()

    if not query:
        return None

    try:

        result = await asyncio.to_thread(
            imdbio.search_title,
            query
        )

        if not result or not result.titles:
            return None

        if bulk:
            return result.titles[:6]

        return result.titles[0]

    except Exception as e:

        print(f"IMDbIO Search Error: {e}")

        return None


# =========================
# ADVANTAGE SPELL CHECK
# =========================

async def advantage_spell_chok(client, msg):

    mv_rqst = msg.text or ""

    if not mv_rqst.strip():
        return

    cleaned_query = re.sub(
        r"\b(pl(i|e)\*?(s|z+|ease|se|ese|(e+)s(e)?)|"
        r"((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|"
        r"br((o|u)h?)\*|mal(ayalam)?|t(h)?amil|file|that|find|"
        r"full\smovie|any(one)|with\ssubtitle(s)?)",
        "",
        mv_rqst,
        flags=re.IGNORECASE
    ).strip()

    if not cleaned_query:
        cleaned_query = mv_rqst.strip()

    # CREATE NOTIFY SESSION

    notify_session = uuid4().hex[:12]

    await search_sessions_col.insert_one({
        "_id": notify_session,
        "query": cleaned_query,
        "chat_id": msg.chat.id,
        "created_at": datetime.utcnow(),
        "kind": "notify"
    })

    # PRIVATE BOT DEEP LINK

    bot_username = client.me.username

    notify_link = (
        f"https://t.me/{bot_username}"
        f"?start=notify_{notify_session}"
    )

    # GOOGLE + NOTIFY BUTTONS

    reqst_gle = quote_plus(mv_rqst)

    google_button = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔔 NOTIFY ME",
                url=notify_link
            )
        ],
        [
            InlineKeyboardButton(
                "🔎 ᴄʜᴇᴄᴋ sᴘᴇʟʟ (ɢᴏᴏɢʟᴇ) 🔎",
                url=f"https://www.google.com/search?q={reqst_gle}"
            )
        ]
    ])

    # IMDbIO MOVIE SUGGESTIONS

    try:

        movies = await get_movie_suggestions(
            cleaned_query,
            bulk=True
        )

    except Exception as e:

        print(f"IMDbIO Error: {e}")

        movies = None

    movielist = []

    seen = set()

    if movies:

        for movie in movies[:6]:

            title = getattr(
                movie,
                "title",
                None
            )

            year = getattr(
                movie,
                "year",
                None
            )

            if not title:
                continue

            title = str(title).strip()

            year_match = re.search(
                r"\b(19\d{2}|20\d{2})\b",
                str(year)
            ) if year else None

            year_text = (
                f" {year_match.group(1)}"
                if year_match else ""
            )

            movie_name = f"{title}{year_text}"

            if movie_name.casefold() not in seen:

                seen.add(movie_name.casefold())

                movielist.append(movie_name)

            if len(movielist) >= 6:
                break

    # SPELL CHECK MESSAGE

    text = (
        "<blockquote>"
        "<b>🚫 ᴏᴛᴛ ɴ/ᴀ ➪ ᴄʜᴇᴄᴋ sᴘᴇʟʟ 🚫</b>\n\n"

        "───────────────\n"

        "<b>➳ ᴍᴏᴠɪᴇ ᴏᴛᴛ ഇറങ്ങിയിട്ടില്ല കേട്ടോ അഥവാ ഇറങ്ങിയിട്ടുണ്ടെങ്കിൽ "
        "താഴെ തന്നിരിക്കുന്ന ശരിയായ spelling ഉപയോഗിച്ച് search തുടരുക.</b>\n"

        "───────────────\n"

        "<b>➳ ᴛʜᴇ ᴍᴏᴠɪᴇ ʜᴀs ɴᴏᴛ ʙᴇᴇɴ ʀᴇʟᴇᴀsᴇᴅ "
        "ᴏɴ ᴀɴʏ ᴏᴛᴛ ᴘʟᴀᴛғᴏʀᴍ ʏᴇᴛ.</b>\n\n"

        "<b>➳ ɪғ ɪᴛ ʜᴀs ʙᴇᴇɴ ʀᴇʟᴇᴀsᴇᴅ, ᴘʟᴇᴀsᴇ ᴛʀʏ "
        "sᴇᴀʀᴄʜɪɴɢ ᴀɢᴀɪɴ ᴜsɪɴɢ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ sᴘᴇʟʟɪɴɢ "
        "ᴘʀᴏᴠɪᴅᴇᴅ ʙᴇʟᴏᴡ.</b>\n\n"

        "<b>➳ ɪғ ʏᴏᴜ sᴛɪʟʟ ᴄᴀɴɴᴏᴛ ғɪɴᴅ ɪᴛ, "
        "ᴘʟᴇᴀsᴇ ᴜsᴇ ᴛʜᴇ ɢᴏᴏɢʟᴇ ʙᴜᴛᴛᴏɴ.</b>"
    )

    # SHOW SUGGESTIONS

    if movielist:

        text += (
            "\n───────────────\n"
            "💡 <b>sᴜɢɢᴇsᴛɪᴏɴs</b>\n\n"
        )

        for index, movie_name in enumerate(
            movielist,
            start=1
        ):

            text += (
                f"<b>{index}.</b> "
                f"<code>{escape(movie_name)}</code>\n"
            )

    else:

        text += (
            "\n━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>sᴜɢɢᴇsᴛɪᴏɴs</b>\n"
            "<i>No suggestions available right now.</i>\n"
        )

    # SEND SPELL CHECK MESSAGE

    await msg.reply_text(
        text=text,
        reply_markup=google_button,
        reply_to_message_id=msg.id,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )


# =========================
# AUTO FILTER
# =========================

@Client.on_message(
    filters.group & filters.text
)
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

            total += await collection.count_documents(
                search_filter
            )

    # MISSING MOVIES + SPELL CHECK

    if not total:

        query_key = re.sub(
            r"[^\w]+",
            " ",
            query.casefold()
        ).strip()

        if query_key:

            await missing_col.update_one(
                {"normalized_name": query_key},
                {
                    "$setOnInsert": {
                        "movie_name": query
                    }
                },
                upsert=True
            )

        try:

            await advantage_spell_chok(
                client,
                message
            )

        except Exception as e:

            print(f"Spelling Check Error: {e}")

        return

    # UPDATE SEARCH STATS

    await stats_col.update_one(
        {"_id": "bot_stats"},
        {"$inc": {"searches": 1}},
        upsert=True
    )

    # CREATE SEARCH SESSION

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
# TEMPORARY SEARCH NOW
# =========================

async def _delete_temporary_result(client, chat_id, message_id):

    await asyncio.sleep(600)

    try:
        await client.delete_messages(chat_id, message_id)
    except Exception as e:
        print(f"Temporary Result Delete Error: {e}")


def _message_link(chat, message_id):

    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}/{message_id}"

    internal_id = str(chat.id)

    if internal_id.startswith("-100"):
        return f"https://t.me/c/{internal_id[4:]}/{message_id}"

    return None


@Client.on_callback_query(
    filters.regex(r"^searchnow:")
)
async def search_now_callback(client, callback_query):

    request_id = callback_query.data.split(":", 1)[1]

    request = await notify_requests_col.find_one({
        "_id": request_id
    })

    if not request or request.get("user_id") != callback_query.from_user.id:
        await callback_query.answer(
            "Request not found!",
            show_alert=True
        )
        return

    query = request.get("movie_name", "").strip()

    search_filter = build_search_filter(query)

    if not search_filter:
        await callback_query.answer(
            "Invalid movie name!",
            show_alert=True
        )
        return

    total = 0

    for collection, _ in DATABASES:
        if collection is not None:
            total += await collection.count_documents(search_filter)

    if not total:
        await callback_query.answer(
            "Movie result not found yet. Please try later.",
            show_alert=True
        )
        return

    target = None

    if UPDATE_GROUP:
        try:
            target = await client.get_chat(UPDATE_GROUP)
        except Exception as e:
            print(f"Search Group Error: {e}")

    if target is None:
        group = await groups_col.find_one({})

        if group:
            try:
                target = await client.get_chat(
                    group.get("username") or group.get("id")
                )
            except Exception as e:
                print(f"Saved Group Error: {e}")

    if target is None:
        await callback_query.answer(
            "Search group is not configured!",
            show_alert=True
        )
        return

    session_id = uuid4().hex

    await search_sessions_col.insert_one({
        "_id": session_id,
        "query": query,
        "chat_id": target.id,
        "created_at": datetime.utcnow(),
        "temporary": True
    })

    total_pages = max(
        1,
        (total + PAGE_SIZE - 1) // PAGE_SIZE
    )

    results = await get_search_results(
        search_filter,
        PAGE_SIZE
    )

    keyboard = get_file_buttons(
        client,
        results[:PAGE_SIZE],
        session_id,
        0,
        total_pages
    )

    result_message = await client.send_message(
        target.id,
        f"🔎 Search Results: {query}\n\n"
        f"📁 Found: {total} Files\n"
        f"📄 Page: 1/{total_pages}",
        reply_markup=keyboard
    )

    asyncio.create_task(
        _delete_temporary_result(
            client,
            target.id,
            result_message.id
        )
    )

    link = _message_link(target, result_message.id)

    if link:
        await callback_query.answer(
            "✅ Search result posted in the group!",
            url=link
        )
    else:
        await callback_query.answer(
            "✅ Result posted. Open the group to view it."
        )
