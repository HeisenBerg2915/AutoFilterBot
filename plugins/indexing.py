import re
import asyncio
import uuid
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMINS, LOG_CHANNEL
from helpers.episode_filter import is_tv_episode
from helpers.database_router import get_target_collections, save_file_to_databases


# Requests and running jobs are kept in memory.
index_requests = {}
index_jobs = {}

MEDIA_TYPES = (
    "document",
    "video",
    "audio",
    "animation",
    "photo",
    "voice",
    "video_note",
)


def parse_telegram_post_link(link):
    """Return (chat reference, last message ID) for a Telegram post URL."""

    match = re.match(
        r"^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/"
        r"(?:(?:s)/)?([^/?#]+)/([0-9]+)(?:\?.*)?$",
        link.strip(),
        re.IGNORECASE,
    )

    if not match:
        return None, None

    channel_part, message_id = match.groups()

    if channel_part == "c":
        return None, None

    if channel_part.startswith("+") or channel_part == "joinchat":
        return None, None

    return channel_part, int(message_id)


def get_forwarded_source(message):
    """Support forwarded channel messages."""

    source_chat = getattr(message, "forward_from_chat", None)
    source_message_id = getattr(message, "forward_from_message_id", None)

    if source_chat and source_message_id:
        return source_chat.id, int(source_message_id)

    origin = getattr(message, "forward_origin", None)

    if origin:
        chat = getattr(origin, "chat", None)
        message_id = getattr(origin, "message_id", None)

        if chat and message_id:
            return chat.id, int(message_id)

    return None, None


def request_keyboard(request_id):
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "✅ Accept",
                callback_data=f"idx:accept:{request_id}"
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"idx:reject:{request_id}"
            ),
        ]]
    )


def database_keyboard(request_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "DB1",
                    callback_data=f"idx:db1:{request_id}"
                ),
                InlineKeyboardButton(
                    "DB2",
                    callback_data=f"idx:db2:{request_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "DB3",
                    callback_data=f"idx:db3:{request_id}"
                ),
                InlineKeyboardButton(
                    "All DBs",
                    callback_data=f"idx:all:{request_id}"
                ),
            ],
        ]
    )


def cancel_keyboard(request_id):
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "⛔ Cancel Indexing",
                callback_data=f"idx:cancel:{request_id}"
            )
        ]]
    )


async def send_index_request(
    client,
    message,
    source_chat,
    last_message_id,
    source_label
):

    if not LOG_CHANNEL:
        await message.reply_text(
            "❌ LOG_CHANNEL configure ചെയ്തിട്ടില്ല."
        )
        return

    request_id = uuid.uuid4().hex[:10]

    index_requests[request_id] = {
        "chat_id": source_chat,
        "last_message_id": int(last_message_id),
        "requester_id": message.from_user.id if message.from_user else 0,
        "requester_name": (
            message.from_user.mention
            if message.from_user
            else "Unknown"
        ),
        "source_label": source_label,
        "status": "pending",
    }

    try:

        await client.send_message(
            LOG_CHANNEL,

            "📥 **New Indexing Request**\n\n"
            f"👤 Requested by: {index_requests[request_id]['requester_name']}\n"
            f"📡 Source: `{source_label}`\n"
            f"🆔 Chat ID: `{source_chat}`\n"
            f"🔢 Last Message ID: `{last_message_id}`\n\n"
            "Moderator, please review this request.",

            reply_markup=request_keyboard(request_id),
        )

        await message.reply_text(
            "✅ Indexing request moderator-ന് അയച്ചു. Approval കാത്തിരിക്കുക."
        )

    except Exception as error:

        index_requests.pop(request_id, None)

        await message.reply_text(
            f"❌ Request അയക്കാൻ കഴിഞ്ഞില്ല: `{error}`"
        )


@Client.on_message(filters.private & filters.command("index"))
async def index_command(client, message):

    if not message.from_user or message.from_user.id not in ADMINS:
        await message.reply_text(
            "❌ ഈ command ഉപയോഗിക്കാൻ അനുവാദമില്ല."
        )
        return

    argument = (
        " ".join(message.command[1:]).strip()
        if len(message.command) > 1
        else ""
    )

    # Channel post link indexing

    if argument:

        chat_ref, last_message_id = parse_telegram_post_link(argument)

        if not chat_ref or not last_message_id:

            await message.reply_text(
                "❌ ശരിയായ post link നൽകുക.\n\n"
                "ഉദാഹരണം:\n"
                "`/index https://t.me/channelusername/1234`"
            )
            return

        try:

            chat = await client.get_chat(chat_ref)

            await send_index_request(
                client,
                message,
                chat.id,
                last_message_id,
                argument
            )

        except Exception as error:

            await message.reply_text(
                f"❌ Channel access ചെയ്യാൻ കഴിഞ്ഞില്ല: `{error}`"
            )

        return

    # Forwarded message indexing

    source_chat_id, source_message_id = get_forwarded_source(message)

    if source_chat_id and source_message_id:

        await send_index_request(
            client,
            message,
            source_chat_id,
            source_message_id,
            f"Forwarded message {source_message_id}",
        )

        return

    # Reply to forwarded post

    replied = message.reply_to_message

    if replied:

        source_chat_id, source_message_id = get_forwarded_source(replied)

        if source_chat_id and source_message_id:

            await send_index_request(
                client,
                message,
                source_chat_id,
                source_message_id,
                f"Forwarded message {source_message_id}",
            )

            return

    await message.reply_text(
        "📌 **Index command**\n\n"
        "1. Channel post link:\n"
        "`/index https://t.me/channelusername/1234`\n\n"
        "2. അല്ലെങ്കിൽ channel post forward ചെയ്ത് "
        "അതിന് reply ആയി `/index` അയക്കുക."
    )


async def run_indexing(
    client,
    request_id,
    status_message,
    target
):

    request = index_requests.get(request_id)

    if not request:

        await status_message.edit_text(
            "❌ Request കണ്ടെത്താനായില്ല. വീണ്ടും /index ചെയ്യുക."
        )

        return

    collections = get_target_collections(target)

    if not collections:

        await status_message.edit_text(
            f"❌ {target.upper()} database configure ചെയ്തിട്ടില്ല അല്ലെങ്കിൽ ലഭ്യമല്ല."
        )

        return

    request["status"] = "running"
    request["cancel"] = False

    checked = 0
    indexed = 0
    duplicates = 0
    skipped = 0
    errors = 0

    last_message_id = request["last_message_id"]
    source_chat_id = request["chat_id"]

    await status_message.edit_text(
        "⏳ **Indexing Started**\n\n"
        f"🗄 Database: `{target.upper()}`\n"
        f"🔢 Message IDs: `1 - {last_message_id}`\n"
        "📁 Indexed: `0`\n"
        "⏭ Skipped: `0`\n"
        "♻️ Duplicates: `0`\n"
        "🔍 Checked: `0`",

        reply_markup=cancel_keyboard(request_id),
    )

    try:

        async for msg in client.iter_messages(
            source_chat_id,
            reverse=True
        ):
            if msg.id > last_message_id:
                break

            if request.get("cancel"):
                break

            checked += 1

            if not msg or getattr(msg, "empty", False):

                skipped += 1
                continue

            media = None
            media_type = None

            for kind in MEDIA_TYPES:

                candidate = getattr(msg, kind, None)

                if candidate:

                    media = candidate
                    media_type = kind
                    break

            if not media:

                skipped += 1
                continue

            file_name = getattr(media, "file_name", None) or ""
            caption = msg.caption or ""

            if is_tv_episode(f"{file_name} {caption}"):

                skipped += 1
                continue

            file_data = {
                "file_id": media.file_id,
                "file_unique_id": media.file_unique_id,
                "file_name": file_name or None,
                "file_size": getattr(media, "file_size", 0) or 0,
                "mime_type": getattr(media, "mime_type", None),
                "file_type": media_type,
                "caption": caption,
                "chat_id": source_chat_id,
                "message_id": msg.id,
                "date": msg.date or datetime.utcnow(),
            }

            try:

                already_in_all = True

                for collection in collections:

                    found = await collection.find_one(
                        {
                            "file_unique_id": media.file_unique_id
                        },
                        {
                            "_id": 1
                        },
                    )

                    if not found:

                        already_in_all = False
                        break

                await save_file_to_databases(
                    file_data,
                    target=target
                )

                if already_in_all:

                    duplicates += 1

                else:

                    indexed += 1

            except Exception as save_error:

                errors += 1

                print(
                    f"Index save error for message {msg.id}: {save_error}"
                )

            # Live progress update

            if checked % 100 == 0:

                try:

                    await status_message.edit_text(
                        "⏳ **Indexing in Progress**\n\n"
                        f"🗄 Database: `{target.upper()}`\n"
                        f"🔍 Checked: `{checked}` / `{last_message_id}`\n"
                        f"📁 Indexed: `{indexed}`\n"
                        f"♻️ Duplicates: `{duplicates}`\n"
                        f"⏭ Skipped: `{skipped}`\n"
                        f"⚠️ Errors: `{errors}`",

                        reply_markup=cancel_keyboard(request_id),
                    )

                except Exception:
                    pass

    except Exception as error:

        request["status"] = "failed"

        await status_message.edit_text(
            "❌ **Indexing Failed**\n\n"
            f"Error: `{error}`\n\n"
            f"🔍 Checked: `{checked}`\n"
            f"📁 Indexed: `{indexed}`\n"
            f"♻️ Duplicates: `{duplicates}`\n"
            f"⏭ Skipped: `{skipped}`\n"
            f"⚠️ Errors: `{errors}`"
        )

        return

    cancelled = bool(request.get("cancel"))

    request["status"] = (
        "cancelled"
        if cancelled
        else "completed"
    )

    await status_message.edit_text(
        f"{'⛔ **Indexing Cancelled**' if cancelled else '✅ **Indexing Completed**'}\n\n"
        f"🗄 Database: `{target.upper()}`\n"
        f"🔍 Checked: `{checked}`\n"
        f"📁 Indexed: `{indexed}`\n"
        f"♻️ Duplicates: `{duplicates}`\n"
        f"⏭ Skipped: `{skipped}`\n"
        f"⚠️ Errors: `{errors}`"
    )


@Client.on_callback_query(
    filters.regex(
        r"^idx:(accept|reject|db1|db2|db3|all|cancel):([a-f0-9]+)$"
    )
)
async def indexing_callbacks(client, query):

    if not query.from_user or query.from_user.id not in ADMINS:

        await query.answer(
            "Not allowed",
            show_alert=True
        )

        return

    action, request_id = query.data.split(":", 2)[1:]

    request = index_requests.get(request_id)

    if not request:

        await query.answer(
            "Request expired or not found.",
            show_alert=True
        )

        return

    # Reject request

    if action == "reject":

        request["status"] = "rejected"

        await query.message.edit_text(
            "❌ **Indexing Request Rejected**"
        )

        await query.answer("Rejected")

        return

    # Accept request

    if action == "accept":

        if request.get("status") != "pending":

            await query.answer(
                "This request was already handled.",
                show_alert=True
            )

            return

        request["status"] = "approved"

        await query.message.edit_text(
            query.message.text
            + "\n\n✅ **Approved. Select destination database:**",

            reply_markup=database_keyboard(request_id),
        )

        await query.answer("Approved")

        return

    # Database selection

    if action in ("db1", "db2", "db3", "all"):

        if request.get("status") != "approved":

            await query.answer(
                "Approve the request first.",
                show_alert=True
            )

            return

        if request_id in index_jobs and not index_jobs[request_id].done():

            await query.answer(
                "Indexing is already running.",
                show_alert=True
            )

            return

        await query.answer("Indexing started")

        status_message = await query.message.reply_text(
            "⏳ Starting indexing..."
        )

        task = asyncio.create_task(
            run_indexing(
                client,
                request_id,
                status_message,
                action
            )
        )

        index_jobs[request_id] = task

        return

    # Cancel indexing

    if action == "cancel":

        request["cancel"] = True

        await query.answer(
            "Cancellation requested"
        )

        return
