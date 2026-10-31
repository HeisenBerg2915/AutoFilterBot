from pyrogram import Client
from pyrogram.types import ChatJoinRequest

from database import reqone, reqtwo


@Client.on_chat_join_request()
async def track_join_request(client, request: ChatJoinRequest):

    user_id = request.from_user.id

    invite = request.invite_link
    invite_url = invite.invite_link if invite else None

    try:

        if invite_url == getattr(client, "req_link1", None):

            await reqone.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )

            print(f"Channel 1 Request Saved: {user_id}")

        elif invite_url == getattr(client, "req_link2", None):

            await reqtwo.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )

            print(f"Channel 2 Request Saved: {user_id}")

    except Exception as e:

        print(f"Join Request Error: {e}")
