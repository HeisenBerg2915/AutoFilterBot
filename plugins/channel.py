from pyrogram import Client, filters

from database import files_col
from config import FILE_CHANNEL
from helpers.episode_filter import is_tv_episode


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
            "file_name": getattr(media, "file_name", None),
            "file_size": media.file_size,
            "mime_type": getattr(media, "mime_type", None),
            "file_type": media_type,
            "caption": message.caption or "",
            "chat_id": message.chat.id,
            "message_id": message.id,
            "date": message.date
        }

        await files_col.update_one(
            {"file_unique_id": media.file_unique_id},
            {"$set": file_data},
            upsert=True
        )

        print(f"File Saved: {media_type}")
        break
