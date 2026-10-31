from pyrogram import Client
from pyrogram.types import ChatJoinRequest

from config import REQ_CHANNEL1, REQ_CHANNEL2
from database import reqone, reqtwo


@Client.on_chat_join_request()
async def track_join_request(client, request: ChatJoinRequest):

    user_id = request.from_user.id
    channel_id = request.chat.id

    invite = request.invite_link
    invite_url = getattr(invite, "invite_link", None) if invite else None

    try:
        if (
            REQ_CHANNEL1 is not None
            and channel_id == REQ_CHANNEL1
            and invite_url == getattr(client, "req_link1", None)
        ):
            await reqone.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )

            print(f"Channel 1 Request Saved: {user_id}")

        elif (
            REQ_CHANNEL2 is not None
            and channel_id == REQ_CHANNEL2
            and invite_url == getattr(client, "req_link2", None)
        ):
            await reqtwo.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )

            print(f"Channel 2 Request Saved: {user_id}")

    except Exception as e:
        print(f"Join Request Error: {e}")
