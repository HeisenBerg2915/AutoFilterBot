import re

from bson import ObjectId
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMINS
from database import files_col, files_col2, files_col3


MEDIA_TYPES = (
    "document", "video", "audio", "photo", "animation",
    "voice", "video_note"
)

DATABASES = {
    "1": ("DB1", files_col),
    "2": ("DB2", files_col2),
    "3": ("DB3", files_col3)
}


def get_media(message):
    if not message:
        return None

    for media_type in MEDIA_TYPES:
        media = getattr(message, media_type, None)

        if media:
            return media

    return None


# DELETE SINGLE FILE OR SEARCH BY NAME
@Client.on_message(
    filters.command("delete") & filters.user(ADMINS)
)
async def delete_file(client, message):

    replied = message.reply_to_message
    media = get_media(replied)

    # OLD REPLY-BASED DELETE
    if media:

        deleted = 0

        for name, collection in DATABASES.values():
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

        return

    # FILE NAME SEARCH
    if not message.text or len(message.text.split(maxsplit=1)) < 2:
        await message.reply_text(
            "⚠️ ഉപയോഗം:\n"
            "/delete Money Heist\n\n"
            "അല്ലെങ്കിൽ File-ന് Reply നൽകി /delete അയക്കുക."
        )
        return

    search_name = message.text.split(maxsplit=1)[1].strip()

    if not search_name:
        await message.reply_text("⚠️ File name നൽകുക.")
        return

    pattern = re.escape(search_name)
    results = []

    for db_number, (db_name, collection) in DATABASES.items():

        if collection is None:
            continue

        cursor = collection.find({
            "$or": [
                {"file_name": {"$regex": pattern, "$options": "i"}},
                {"filename": {"$regex": pattern, "$options": "i"}}
            ]
        }).limit(10)

        async for doc in cursor:
            file_name = (
                doc.get("file_name")
                or doc.get("filename")
                or "Unknown File"
            )

            results.append({
                "db": db_number,
                "db_name": db_name,
                "id": str(doc["_id"]),
                "name": file_name
            })

    if not results:
        await message.reply_text(
            f"❌ No files found for:\n{search_name}"
        )
        return

    buttons = []

    for item in results:
        buttons.append([
            InlineKeyboardButton(
                f"📁 {item['name'][:45]} ({item['db_name']})",
                callback_data=f"delfile_pick:{item['db']}:{item['id']}"
            )
        ])

    await message.reply_text(
        f"🔎 Search: {search_name}\n"
        f"📁 Found: {len(results)} files\n\n"
        "Delete ചെയ്യേണ്ട File തിരഞ്ഞെടുക്കുക:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.DISABLED
    )


# SELECT FILE
@Client.on_callback_query(
    filters.regex(r"^delfile_pick:")
)
async def delete_file_pick(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    try:
        _, db_number, file_id = query.data.split(":")

        if db_number not in DATABASES:
            raise ValueError

        db_name, collection = DATABASES[db_number]

        if collection is None:
            await query.answer("Database not connected!", show_alert=True)
            return

        doc = await collection.find_one({
            "_id": ObjectId(file_id)
        })

        if not doc:
            await query.answer("File not found!", show_alert=True)
            return

        file_name = (
            doc.get("file_name")
            or doc.get("filename")
            or "Unknown File"
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⚠️ CONFIRM DELETE",
                    callback_data=f"delfile_confirm:{db_number}:{file_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ CANCEL",
                    callback_data="delfile_cancel"
                )
            ]
        ])

        await query.message.edit_text(
            f"⚠️ CONFIRM FILE DELETE?\n\n"
            f"📁 File: {file_name}\n"
            f"🗄️ Database: {db_name}\n\n"
            "Are you sure?",
            reply_markup=buttons,
            parse_mode=ParseMode.DISABLED
        )

        await query.answer()

    except Exception:
        await query.answer("Something went wrong!", show_alert=True)


# CONFIRM FILE DELETE
@Client.on_callback_query(
    filters.regex(r"^delfile_confirm:")
)
async def delete_file_confirm(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    try:
        _, db_number, file_id = query.data.split(":")

        if db_number not in DATABASES:
            raise ValueError

        db_name, collection = DATABASES[db_number]

        if collection is None:
            await query.answer("Database not connected!", show_alert=True)
            return

        result = await collection.delete_one({
            "_id": ObjectId(file_id)
        })

        if result.deleted_count:
            await query.answer("File deleted!")

            await query.message.edit_text(
                f"✅ File successfully deleted!\n\n"
                f"🗄️ Database: {db_name}\n"
                f"🗑️ Deleted records: 1"
            )
        else:
            await query.answer("File not found!", show_alert=True)

    except Exception:
        await query.answer("Delete failed!", show_alert=True)


# CANCEL FILE DELETE
@Client.on_callback_query(
    filters.regex(r"^delfile_cancel$")
)
async def delete_file_cancel(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    await query.answer("Cancelled")

    await query.message.edit_text(
        "❎ Delete operation cancelled."
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
