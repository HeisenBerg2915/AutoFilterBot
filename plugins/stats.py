from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    db,
    db2,
    db3,
    users_col,
    groups_col,
    files_col,
    files_col2,
    files_col3,
    stats_col
)


# MongoDB Atlas Free Cluster Storage Limit
STORAGE_LIMIT_MB = 512
BYTES_PER_MB = 1024 * 1024


def format_mb(size_bytes):
    return round(size_bytes / BYTES_PER_MB, 2)


async def get_database_stats(database, collection):
    if database is None or collection is None:
        return {
            "files": 0,
            "used": 0,
            "free": STORAGE_LIMIT_MB,
            "connected": False
        }

    try:
        total_files = await collection.count_documents({})

        db_stats = await database.command("dbStats")

        # MongoDB allocated data and index storage
        used_bytes = (
            db_stats.get("storageSize", 0)
            + db_stats.get("indexSize", 0)
        )

        used_mb = format_mb(used_bytes)

        free_mb = max(
            0,
            round(STORAGE_LIMIT_MB - used_mb, 2)
        )

        return {
            "files": total_files,
            "used": used_mb,
            "free": free_mb,
            "connected": True
        }

    except Exception as e:
        print(f"Database Stats Error: {e}")

        return {
            "files": 0,
            "used": 0,
            "free": STORAGE_LIMIT_MB,
            "connected": False
        }


@Client.on_callback_query(filters.regex("^stats$"))
async def stats_callback(client, query):

    await query.answer("Loading Statistics...")

    # DB1, DB2, DB3 Statistics
    db1_stats = await get_database_stats(db, files_col)
    db2_stats = await get_database_stats(db2, files_col2)
    db3_stats = await get_database_stats(db3, files_col3)

    # Total Files from all databases
    total_files = (
        db1_stats["files"]
        + db2_stats["files"]
        + db3_stats["files"]
    )

    # Users and Groups (Main Database)
    total_users = await users_col.count_documents({})
    total_groups = await groups_col.count_documents({})

    # Total Searches
    stats = await stats_col.find_one({"_id": "bot_stats"})
    total_searches = stats.get("searches", 0) if stats else 0

    # Database Status
    def status_text(data):
        return "Connected" if data["connected"] else "Not Connected"

    text = (
        "📊 **BOT STATISTICS**\n\n"

        f"📁 **Total Files From All Databases:** "
        f"`{total_files:,}`\n\n"

        "👥 **BOT USERS AND CHATS COUNT**\n"
        f"👤 Total Users: `{total_users:,}`\n"
        f"👨‍👩‍👧 Total Chats: `{total_groups:,}`\n"
        f"🔍 Total Searches: `{total_searches:,}`\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        " **1 DATABASE STATISTICS**\n"
        f"📁 Total Files: `{db1_stats['files']:,}`\n"
        f"💾 Used Storage: `{db1_stats['used']} MB`\n"
        f"🆓 Free Storage: `{db1_stats['free']} MB`\n"
        f"🔌 Status: `{status_text(db1_stats)}`\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        " **2 DATABASE STATISTICS**\n"
        f"📁 Total Files: `{db2_stats['files']:,}`\n"
        f"💾 Used Storage: `{db2_stats['used']} MB`\n"
        f"🆓 Free Storage: `{db2_stats['free']} MB`\n"
        f"🔌 Status: `{status_text(db2_stats)}`\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        " **3 DATABASE STATISTICS**\n"
        f"📁 Total Files: `{db3_stats['files']:,}`\n"
        f"💾 Used Storage: `{db3_stats['used']} MB`\n"
        f"🆓 Free Storage: `{db3_stats['free']} MB`\n"
        f"🔌 Status: `{status_text(db3_stats)}`\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "💾 **Database:** MongoDB\n"
        "🤖 **Bot Status:** Running"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="stats"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back_home"
            )
        ]
    ])

    await query.message.edit_text(
        text,
        reply_markup=buttons
    )


@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start(client, query):

    user = query.from_user

    await query.answer()

    text = (
        f"👋 Hello {user.mention}!\n\n"
        "🎬 Welcome to Auto Filter Bot!\n\n"
        "🔍 Search your favourite movies and files easily."
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add Me To Your Group",
                url=f"https://t.me/{client.me.username}?startgroup=true"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Stats",
                callback_data="stats"
            )
        ]
    ])

    await query.message.edit_text(
        text,
        reply_markup=buttons
    )
