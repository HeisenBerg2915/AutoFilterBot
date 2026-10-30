from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMINS
from database import files_col


MEDIA_TYPES = (
    "document", "video", "audio", "photo", "animation",
    "voice", "video_note"
)


def get_media(message):
    if not message:
        return None

    for media_type in MEDIA_TYPES:
        media = getattr(message, media_type, None)

        if media:
            return media

    return None


# DELETE SINGLE FILE
@Client.on_message(
    filters.command("delete") & filters.user(ADMINS)
)
async def delete_file(client, message):

    replied = message.reply_to_message
    media = get_media(replied)

    if not media:
        await message.reply_text(
            "⚠️ Delete ചെയ്യേണ്ട File-ന് Reply നൽകി /delete അയക്കുക."
        )
        return

    result = await files_col.delete_one({
        "$or": [
            {"file_unique_id": media.file_unique_id},
            {"file_id": media.file_id}
        ]
    })

    if result.deleted_count:
        await message.reply_text(
            "✅ File successfully deleted from database!"
        )
    else:
        await message.reply_text(
            "❌ File not found in database."
        )


# DELETE ALL FILES
@Client.on_message(
    filters.command("deleteall") & filters.user(ADMINS)
)
async def delete_all_indexed_files(client, message):

    total = await files_col.count_documents({})

    if total == 0:
        await message.reply_text(
            "📁 No indexed files found!"
        )
        return

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚠️ YES, DELETE ALL",
                callback_data="confirm_delete_all_files"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ CANCEL",
                callback_data="cancel_delete_all_files"
            )
        ]
    ])

    await message.reply_text(
        f"⚠️ DELETE ALL FILES?\n\n"
        f"Total Files: {total}\n\n"
        "Are you sure?",
        reply_markup=buttons
    )


# CONFIRM DELETE ALL
@Client.on_callback_query(
    filters.regex(r"^(confirm|cancel)_delete_all_files$")
)
async def delete_all_callback(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:
        await query.answer(
            "⛔ Unauthorized!",
            show_alert=True
        )
        return

    if query.data == "cancel_delete_all_files":

        await query.answer("Cancelled")

        await query.message.edit_text(
            "❎ Delete operation cancelled."
        )
        return

    result = await files_col.delete_many({})

    await query.answer("Completed")

    await query.message.edit_text(
        f"✅ Database Cleanup Complete!\n\n"
        f"🗑️ Deleted Files: {result.deleted_count}"
    )
