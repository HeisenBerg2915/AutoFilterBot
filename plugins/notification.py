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
# SETTINGS
# =====================================

GROUP_LINK = os.getenv("NOTIFICATION_GROUP_LINK", "")

BATCH_WAIT = 60

pending_batches = {}
batch_tasks = {}


# =====================================
# FILE SIZE
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


# =====================================
# CLEAN MOVIE NAME
# =====================================

def clean_movie_name(name):

    name = os.path.splitext(name)[0]

    name = re.sub(
        r"(2160p|4k|1080p|720p|480p|360p)",
        "",
        name,
        flags=re.IGNORECASE
    )

    name = re.sub(
        r"\b(Malayalam|Tamil|Telugu|Hindi|English|Kannada)\b",
        "",
        name,
        flags=re.IGNORECASE
    )

    name = re.sub(
        r"\b\d+(\.\d+)?\s*(GB|MB|KB)\b",
        "",
        name,
        flags=re.IGNORECASE
    )

    name = re.sub(r"[\[\](){}._-]+", " ", name)

    name = re.sub(r"\s+", " ", name)

    return name.strip()


# =====================================
# FILE DETAILS
# =====================================

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

    file_name = getattr(media, "file_name", None)

    caption = message.caption or ""

    if file_name:
        original_name = os.path.splitext(file_name)[0]
    else:
        original_name = caption.split("\n")[0].strip()

    movie_name = clean_movie_name(original_name)

    if not movie_name:
        movie_name = "New Movie"

    combined_text = original_name + " " + caption

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
# SEND BATCH NOTIFICATION
# =====================================

async def send_movie_notification(client, details_list):

    if not details_list:
        return

    movie_name = details_list[0]["movie_name"]

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎬 NEW MOVIE AVAILABLE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📂 Movie: {movie_name}\n\n"
    )

    for index, details in enumerate(details_list, 1):

        text += (
            f"📁 File {index}\n"
            f"🎥 Quality: {details['quality']}\n"
            f"🌐 Language: {details['language']}\n"
            f"📦 Size: {format_size(details['file_size'])}\n\n"
        )

    text += (
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

    async for user in users_col.find({}, {"id": 1}):

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
        "\n========== BATCH NOTIFICATION REPORT ==========\n"
        f"Movie: {movie_name}\n"
        f"Files: {len(details_list)}\n"
        f"Success: {success}\n"
        f"Failed: {failed}\n"
        "=============================================="
    )


# =====================================
# BATCH TIMER
# =====================================

async def process_batch(client, batch_key):

    try:

        await asyncio.sleep(BATCH_WAIT)

        details_list = pending_batches.pop(
            batch_key,
            []
        )

        batch_tasks.pop(batch_key, None)

        if details_list:

            await send_movie_notification(
                client,
                details_list
            )

            print(
                f"Batch Completed: {details_list[0]['movie_name']}"
            )

    except asyncio.CancelledError:

        return

    except Exception as e:

        print(f"Batch Processing Error: {e}")


# =====================================
# ADD FILE TO BATCH
# =====================================

async def add_to_batch(client, details):

    batch_key = details["movie_name"].lower().strip()

    if batch_key not in pending_batches:
        pending_batches[batch_key] = []

    pending_batches[batch_key].append(details)

    old_task = batch_tasks.get(batch_key)

    if old_task and not old_task.done():

        old_task.cancel()

    batch_tasks[batch_key] = asyncio.create_task(
        process_batch(client, batch_key)
    )

    print(
        f"File Added To Batch: {details['movie_name']} "
        f"| Total Files: {len(pending_batches[batch_key])}"
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

    # SAVE FILE

    try:

        await notification_files_col.insert_one(details)

    except DuplicateKeyError:

        print("Duplicate File Skipped")

        return

    except Exception as e:

        print(f"MongoDB Save Error: {e}")

        return

    print(
        "Notification File Saved:",
        details["movie_name"]
    )

    # ADD TO 60 SECOND BATCH

    await add_to_batch(
        client,
        details
    )
