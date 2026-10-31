from pyrogram import Client
from pyrogram.types import ChatJoinRequest

from database import reqone, reqtwo


@Client.on_chat_join_request()
async def track_join_request(client, request: ChatJoinRequest):

    user_id = request.from_user.id
    chat_id = request.chat.id

    invite = request.invite_link

    if not invite:
        print(f"Join Request Without Invite Link: {user_id}")
        return

    invite_url = invite.invite_link

    print("========== JOIN REQUEST DEBUG ==========")
    print("USER ID:", user_id)
    print("CHAT ID:", chat_id)
    print("RECEIVED LINK:", repr(invite_url))
    print("CONFIG LINK 1:", repr(getattr(client, "req_link1", None)))
    print("CONFIG LINK 2:", repr(getattr(client, "req_link2", None)))
    print("========================================")

    try:

        link1 = getattr(client, "req_link1", None)
        link2 = getattr(client, "req_link2", None)

        # CHANNEL 1 REQUEST
        if link1 and invite_url == link1:

            await reqone.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "channel_id": chat_id,
                        "invite_link": invite_url
                    }
                },
                upsert=True
            )

            print(f"✅ CHANNEL 1 REQUEST SAVED: {user_id}")

        # CHANNEL 2 REQUEST
        elif link2 and invite_url == link2:

            await reqtwo.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "channel_id": chat_id,
                        "invite_link": invite_url
                    }
                },
                upsert=True
            )

            print(f"✅ CHANNEL 2 REQUEST SAVED: {user_id}")

        else:

            print(f"⚠️ UNKNOWN INVITE LINK: {user_id}")

    except Exception as e:

        print(
            f"❌ JOIN REQUEST ERROR: {type(e).__name__}: {e}"
        )
