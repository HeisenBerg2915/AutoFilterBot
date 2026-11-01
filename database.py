from motor.motor_asyncio import AsyncIOMotorClient

from config import (
    MONGO_URL,
    DB_NAME,
    MONGO_URL2,
    DB_NAME2,
    MONGO_URL3,
    DB_NAME3
)

if not MONGO_URL:
    raise ValueError("MONGO_URL is missing!")

# DATABASE 1
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]

reqone = db["reqone"]
reqtwo = db["reqtwo"]

users_col = db["users"]
groups_col = db["groups"]
files_col = db["files"]
notification_files_col = db["notification_files"]
stats_col = db["stats"]
search_sessions_col = db["search_sessions"]

missing_col = db["missing_movies"]
notify_requests_col = db["notify_requests"]

# DATABASE 2
mongo_client2 = None
db2 = None
files_col2 = None

if MONGO_URL2:
    mongo_client2 = AsyncIOMotorClient(MONGO_URL2)
    db2 = mongo_client2[DB_NAME2]
    files_col2 = db2["files"]

# DATABASE 3
mongo_client3 = None
db3 = None
files_col3 = None

if MONGO_URL3:
    mongo_client3 = AsyncIOMotorClient(MONGO_URL3)
    db3 = mongo_client3[DB_NAME3]
    files_col3 = db3["files"]


async def init_db():

    await users_col.create_index("id", unique=True)
    await groups_col.create_index("id", unique=True)

    await files_col.create_index("file_id")
    await files_col.create_index("file_name")
    await files_col.create_index("file_size")

    await notification_files_col.create_index(
        "file_unique_id",
        unique=True
    )

    await reqone.create_index("user_id", unique=True)
    await reqtwo.create_index("user_id", unique=True)

    await notify_requests_col.create_index(
        [("user_id", 1), ("normalized_name", 1)],
        unique=True
    )

    await notify_requests_col.create_index("normalized_name")

    await search_sessions_col.create_index(
        "created_at",
        expireAfterSeconds=7200
    )

    if files_col2 is not None:
        await files_col2.create_index("file_id")
        await files_col2.create_index("file_name")
        await files_col2.create_index("file_size")

    if files_col3 is not None:
        await files_col3.create_index("file_id")
        await files_col3.create_index("file_name")
        await files_col3.create_index("file_size")

    print("MongoDB Connected Successfully!")


async def close_db():

    mongo_client.close()

    if mongo_client2 is not None:
        mongo_client2.close()

    if mongo_client3 is not None:
        mongo_client3.close()
