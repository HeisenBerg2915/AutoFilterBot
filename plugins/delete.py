from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMINS
from database import files_col, files_col2, files_col3


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


# DELETE SINGLE FILE FROM ALL DATABASES
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

    collections = [files_col, files_col2, files_col3]

    deleted = 0

    for collection in collections:
        if collection is None:
            continue

        result = await collection.delete_many({
            "$or": [
                {"file_unique_id": media.file_unique_id},
                {"file_id": media.file_id}
            ]
        })

        deleted += result.deleted_count

    if deleted:
        await message.reply_text(
            f"✅ File successfully deleted!\n"
            f"🗑️ Deleted records: {deleted}"
        )
    else:
        await message.reply_text(
            "❌ File not found in databases."
        )


# DELETE ALL FILES FROM ALL DATABASES
@Client.on_message(
    filters.command("deleteall") & filters.user(ADMINS)
)
async def delete_all_indexed_files(client, message):

    collections = [
        ("DB1", files_col),
        ("DB2", files_col2),
        ("DB3", files_col3)
    ]

    total = 0

    for name, collection in collections:
        if collection is not None:
            total += await collection.count_documents({
                "_id": {
                    "$ne": "__index_round_robin_state__"
                }
            })

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
        f"DB1 + DB2 + DB3\n"
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

    collections = [
        ("DB1", files_col),
        ("DB2", files_col2),
        ("DB3", files_col3)
    ]

    deleted_total = 0
    report = []

    for name, collection in collections:

        if collection is None:
            report.append(f"{name}: Not connected")
            continue

        result = await collection.delete_many({
            "_id": {
                "$ne": "__index_round_robin_state__"
            }
        })

        deleted_total += result.deleted_count

        report.append(
            f"{name}: {result.deleted_count} deleted"
        )

    await query.answer("Completed")

    await query.message.edit_text(
        "✅ Database Cleanup Complete!\n\n"
        + "\n".join(report)
        + f"\n\n🗑️ Total Deleted: {deleted_total}"
    )
