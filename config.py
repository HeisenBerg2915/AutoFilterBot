import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# MongoDB Configuration
MONGO_URL = os.getenv("MONGO_URL", "")
DB_NAME = os.getenv("DB_NAME", "autofilter")

# Bot Configuration
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

# Admin Configuration
ADMINS = [
    int(x) for x in os.getenv("ADMINS", "").split()
    if x.strip().isdigit()
]

# Channel & Group Configuration
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "0"))
UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "")
UPDATE_GROUP = os.getenv("UPDATE_GROUP", "")

# File Settings
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL", "0"))

# Search Settings
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))

# Force Subscription
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "")
