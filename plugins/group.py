from pyrogram import Client, filters

from database import groups_col


@Client.on_message(filters.group, group=1)
async def save_group(client, message):

    chat = message.chat

    group_data = {
        "id": chat.id,
        "title": chat.title,
        "username": chat.username,
        "type": str(chat.type)
    }

    await groups_col.update_one(
        {"id": chat.id},
        {"$set": group_data},
        upsert=True
    )


@Client.on_message(filters.command("id") & filters.group)
async def group_id(client, message):

    await message.reply_text(
        f"🆔 Group ID: `{message.chat.id}`"
    )
