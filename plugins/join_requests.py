from pyrogram import Client
from pyrogram.types import ChatJoinRequest

from database import reqone, reqtwo


# CHANNEL IDs
CHANNEL_1_ID = -1004393586601
CHANNEL_2_ID = -1003951518872


@Client.on_chat_join_request()
async def track_join_request(client, request: ChatJoinRequest):

    user_id = request.from_user.id
    chat_id = request.chat.id

    print("========== JOIN REQUEST DEBUG ==========")
    print("USER ID:", user_id)
    print("CHAT ID:", chat_id)
    print("========================================")

    try:

        # CHANNEL 1 REQUEST
        if chat_id == CHANNEL_1_ID:

            await reqone.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "channel_id": chat_id
                    }
                },
                upsert=True
            )

            print(f"✅ CHANNEL 1 REQUEST SAVED: {user_id}")

        # CHANNEL 2 REQUEST
        elif chat_id == CHANNEL_2_ID:

            await reqtwo.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "channel_id": chat_id
                    }
                },
                upsert=True
            )

            print(f"✅ CHANNEL 2 REQUEST SAVED: {user_id}")

        else:

            print(f"⚠️ UNKNOWN CHANNEL ID: {chat_id}")

    except Exception as e:

        print(
            f"❌ JOIN REQUEST ERROR: {type(e).__name__}: {e}"
        )
