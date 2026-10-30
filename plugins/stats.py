from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import users_col, groups_col, files_col, stats_col


@Client.on_callback_query(filters.regex("^stats$"))
async def stats_callback(client, query):

    await query.answer("Loading Statistics...")

    total_users = await users_col.count_documents({})
    total_groups = await groups_col.count_documents({})
    total_files = await files_col.count_documents({})

    stats = await stats_col.find_one({"_id": "bot_stats"})

    total_searches = stats.get("searches", 0) if stats else 0

    text = (
        "📊 **BOT STATISTICS**\n\n"
        f"👥 Total Users: `{total_users}`\n"
        f"👨‍👩‍👧 Total Groups: `{total_groups}`\n"
        f"📁 Total Files: `{total_files}`\n"
        f"🔍 Total Searches: `{total_searches}`\n\n"
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
                callback_data="back_to_start"
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
