from pyrogram import filters
from bot import app
from database import files_col
from config import FILE_CHANNEL


@app.on_message(filters.channel)
async def save_channel_files(client, message):

    # Check File Channel
    if FILE_CHANNEL and message.chat.id != FILE_CHANNEL:
        return

    media_types = [
        "document",
        "video",
        "audio",
        "photo",
        "animation",
        "voice",
        "video_note",
        "sticker"
    ]

    media = None
    file_type = None

    for media_type in media_types:
        media = getattr(message, media_type, None)

        if media:
            file_type = media_type
            break

    if not media:
        return

    # File Details
    file_data = {
        "file_id": media.file_id,
        "file_unique_id": media.file_unique_id,
        "file_name": getattr(media, "file_name", None),
        "file_size": media.file_size,
        "mime_type": getattr(media, "mime_type", None),
        "file_type": file_type,
        "caption": message.caption or "",
        "chat_id": message.chat.id,
        "message_id": message.id,
        "date": message.date,
        "media_group_id": message.media_group_id
    }

    # Save to MongoDB
    await files_col.update_one(
        {"file_unique_id": media.file_unique_id},
        {"$set": file_data},
        upsert=True
    )

    print(
        f"File Saved: {file_data['file_name'] or file_type}"
    )
