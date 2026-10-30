import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# MongoDB Configuration

# EXISTING DATABASE - DO NOT CHANGE
MONGO_URL = os.getenv("MONGO_URL", "")
DB_NAME = os.getenv("DB_NAME", "autofilter")

# NEW DATABASE 2
MONGO_URL2 = os.getenv("MONGO_URL2", "")
DB_NAME2 = os.getenv("DB_NAME2", "autofilter_db2")

# NEW DATABASE 3
MONGO_URL3 = os.getenv("MONGO_URL3", "")
DB_NAME3 = os.getenv("DB_NAME3", "autofilter_db3")

# Bot Configuration
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

# Admin Configuration
ADMINS = [
    int(x) for x in os.getenv("ADMINS", "").split()
    if x.strip().isdigit()
]

# Channel & Group Configuration
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1004304801193"))
UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "")
UPDATE_GROUP = os.getenv("UPDATE_GROUP", "")

# File Settings
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL", "0"))

# Search Settings
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))

# Force Subscription
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "")
