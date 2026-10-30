from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, DB_NAME

if not MONGO_URL:
    raise ValueError("MONGO_URL is missing!")

# MongoDB Connection
mongo_client = AsyncIOMotorClient(MONGO_URL)

# Database
db = mongo_client[DB_NAME]

# Collections
users_col = db["users"]
groups_col = db["groups"]
files_col = db["files"]
stats_col = db["stats"]

# Initialize Database
async def init_db():
    await users_col.create_index("id", unique=True)
    await groups_col.create_index("id", unique=True)
    await files_col.create_index("file_id")
    await files_col.create_index("file_name")
    await files_col.create_index("file_size")
    
    print("MongoDB Connected Successfully!")

# Close Database
async def close_db():
    mongo_client.close()
