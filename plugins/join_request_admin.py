from pyrogram import Client, filters, enums

from config import ADMINS
from database import reqone, reqtwo


@Client.on_message(
    filters.command("totalreq") & filters.private & filters.user(ADMINS)
)
async def total_requests(client, message):

    count_one = await reqone.count_documents({})
    count_two = await reqtwo.count_documents({})

    title_one = "Channel 1"
    title_two = "Channel 2"

    await message.reply_text(
        "<b>📊 TOTAL JOIN REQUESTS</b>\n\n"
        f"📢 {title_one}: <code>{count_one}</code>\n"
        f"📢 {title_two}: <code>{count_two}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(
    filters.command("purge_one") & filters.private & filters.user(ADMINS)
)
async def purge_one(client, message):

    result = await reqone.delete_many({})

    await message.reply_text(
        f"✅ Channel 1 Database Cleared!\n"
        f"Deleted: {result.deleted_count}"
    )


@Client.on_message(
    filters.command("purge_two") & filters.private & filters.user(ADMINS)
)
async def purge_two(client, message):

    result = await reqtwo.delete_many({})

    await message.reply_text(
        f"✅ Channel 2 Database Cleared!\n"
        f"Deleted: {result.deleted_count}"
    )


@Client.on_message(
    filters.command("reqlinks") & filters.private & filters.user(ADMINS)
)
async def request_links(client, message):

    link1 = getattr(client, "req_link1", None)
    link2 = getattr(client, "req_link2", None)

    await message.reply_text(
        "<b>🔗 JOIN REQUEST LINKS</b>\n\n"
        f"Channel 1: {link1 or 'Not configured'}\n\n"
        f"Channel 2: {link2 or 'Not configured'}",
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )
