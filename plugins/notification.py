import os
import re
import asyncio

from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.errors import FloodWait
from pymongo.errors import DuplicateKeyError

from config import NOTIFICATION_FILE_CHANNEL

from database import (
    notification_files_col,
    users_col
)


# =====================================
# NOTIFICATION GROUP LINK
# =====================================

GROUP_LINK = os.getenv(
    "NOTIFICATION_GROUP_LINK", ""
)


# =====================================
# FILE DETAILS
# =====================================

def format_size(size):

    if not size:
        return "Unknown"

    size = float(size)

    for unit in ["B", "KB", "MB", "GB", "TB"]:

        if size < 1024:
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} PB"


def get_file_details(message):

    media_types = [
        "document",
        "video",
        "audio",
        "photo",
        "animation",
        "voice",
        "video_note"
    ]

    media = None
    media_type = None

    for item in media_types:

        value = getattr(message, item, None)

        if value:

            media = value
            media_type = item
            break

    if not media:
        return None

    file_name = getattr(
        media,
        "file_name",
        None
    )

    caption = message.caption or ""

    if file_name:

        movie_name = os.path.splitext(
            file_name
        )[0]

    else:

        movie_name = caption.split("\n")[0].strip()

    if not movie_name:
        movie_name = "New Movie"

    combined_text = movie_name + " " + caption

    quality_match = re.search(
        r"(2160p|4k|1080p|720p|480p|360p)",
        combined_text,
        re.IGNORECASE
    )

    quality = (
        quality_match.group(1)
        if quality_match
        else "Not Available"
    )

    languages = [
        "Malayalam",
        "Tamil",
        "Telugu",
        "Hindi",
        "English",
        "Kannada"
    ]

    language = "Not Available"

    for lang in languages:

        if re.search(
            r"\b" + lang + r"\b",
            combined_text,
            re.IGNORECASE
        ):

            language = lang
            break

    return {
        "movie_name": movie_name,
        "file_name": file_name,
        "file_id": media.file_id,
        "file_unique_id": media.file_unique_id,
        "file_size": media.file_size,
        "mime_type": getattr(media, "mime_type", None),
        "file_type": media_type,
        "quality": quality,
        "language": language,
        "caption": caption,
        "chat_id": message.chat.id,
        "message_id": message.id,
        "date": message.date,
        "created_at": datetime.utcnow()
    }


# =====================================
# SEND NOTIFICATION TO USERS
# =====================================

async def send_movie_notification(client, details):

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎬 NEW MOVIE AVAILABLE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"📂 Movie: {details['movie_name']}\n\n"

        f"🎥 Quality: {details['quality']}\n"
        f"🌐 Language: {details['language']}\n"
        f"📦 Size: {format_size(details['file_size'])}\n\n"

        "🍿 NOW AVAILABLE !\n\n"

        "━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = None

    if GROUP_LINK:

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔍 SEARCH NOW",
                    url=GROUP_LINK
                )
            ]
        ])

    success = 0
    failed = 0

    async for user in users_col.find(
        {},
        {"id": 1}
    ):

        user_id = user.get("id")

        if not user_id:
            continue

        try:

            await client.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard
            )

            success += 1

        except FloodWait as e:

            await asyncio.sleep(e.value + 1)

            try:

                await client.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=keyboard
                )

                success += 1

            except Exception as error:

                failed += 1

                print(
                    f"Notification Error {user_id}: {error}"
                )

        except Exception as e:

            failed += 1

            print(
                f"Notification Error {user_id}: {e}"
            )

        await asyncio.sleep(0.05)

    print(
        "\n========== NOTIFICATION REPORT ==========\n"
        f"Movie: {details['movie_name']}\n"
        f"Success: {success}\n"
        f"Failed: {failed}\n"
        "========================================="
    )


# =====================================
# NEW FILE CHANNEL HANDLER
# =====================================

@Client.on_message(
    filters.channel,
    group=10
)
async def notification_file_handler(client, message):

    if not NOTIFICATION_FILE_CHANNEL:
        return

    if message.chat.id != NOTIFICATION_FILE_CHANNEL:
        return

    details = get_file_details(message)

    if not details:
        return

    unique_id = details.get("file_unique_id")

    if not unique_id:
        return

    # CHECK DUPLICATE

    old_file = await notification_files_col.find_one(
        {
            "file_unique_id": unique_id
        }
    )

    if old_file:

        print(
            "Duplicate Notification File Skipped:",
            details["movie_name"]
        )

        return

    # SAVE TO SEPARATE DATABASE COLLECTION

    try:

        await notification_files_col.insert_one(
            details
        )

    except DuplicateKeyError:

        print("Duplicate File Skipped")

        return

    except Exception as e:

        print(
            f"MongoDB Save Error: {e}"
        )

        return

    print(
        "Notification File Saved:",
        details["movie_name"]
    )

    # SEND TO ALL STARTED USERS

    await send_movie_notification(
        client,
        details
    )

    print(
        "Movie Notification Completed!"
  )
