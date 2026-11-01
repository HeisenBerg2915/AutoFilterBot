from pyrogram import Client, filters

from config import FILE_CHANNEL
from database import missing_col
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import re

from helpers.episode_filter import is_tv_episode
from helpers.database_router import save_file_to_databases


@Client.on_message(filters.channel)
async def save_channel_files(client, message):

    if FILE_CHANNEL and message.chat.id != FILE_CHANNEL:
        return

    media_types = [
        "document",
        "video",
        "audio",
        "photo",
        "animation",
        "voice",
        "video_note"
    ]

    for media_type in media_types:

        media = getattr(message, media_type, None)

        if not media:
            continue

        file_name = getattr(media, "file_name", None)

        if is_tv_episode(file_name):
            print(f"TV Episode Skipped: {file_name}")
            continue

        file_data = {
            "file_id": media.file_id,
            "file_unique_id": media.file_unique_id,
            "file_name": file_name,
            "file_size": media.file_size,
            "mime_type": getattr(media, "mime_type", None),
            "file_type": media_type,
            "caption": message.caption or "",
            "chat_id": message.chat.id,
            "message_id": message.id,
            "date": message.date
        }

        saved_count = await save_file_to_databases(
            file_data,
            target="db1"
        )

        if saved_count:
            print(f"File Saved: {file_name or media_type}")
            await notify_matching_users(
                client,
                file_name or message.caption or ""
            )
        else:
            print("File Save Failed: No database available")

        break


async def notify_matching_users(client, uploaded_name):

    uploaded_norm = re.sub(
        r"[^\w]+",
        " ",
        uploaded_name.casefold()
    ).strip()

    if not uploaded_norm:
        return

    requests = await missing_col.find(
        {"notified": False}
    ).to_list(length=None)

    for request in requests:

        wanted = request.get("normalized_name", "")

        if len(wanted) < 3:
            continue

        if not (
            wanted in uploaded_norm
            or uploaded_norm in wanted
        ):
            continue

        try:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⚡ SEARCH NOW",
                        callback_data=f"searchnow:{request['_id']}"
                    )
                ]
            ])

            await client.send_message(
                request["user_id"],
                "🎉 MOVIE NOW AVAILABLE!\n\n"
                f"🎬 {request.get('movie_name', uploaded_name)}\n\n"
                "നിങ്ങൾ ആവശ്യപ്പെട്ട Movie ഇപ്പോൾ ലഭ്യമാണ്!",
                reply_markup=keyboard
            )

            await missing_col.update_one(
                {"_id": request["_id"]},
                {
                    "$set": {
                        "notified": True,
                        "notified_at": datetime.utcnow(),
                        "uploaded_name": uploaded_name
                    }
                }
            )

        except Exception as e:
            print(
                f"Notify User Error "
                f"({request.get('user_id')}): {e}"
            )
