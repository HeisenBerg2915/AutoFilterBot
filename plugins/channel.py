from pyrogram import Client, filters

from config import FILE_CHANNEL
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
        else:
            print("File Save Failed: No database available")

        break
