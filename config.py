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
# Accept either a numeric channel ID (-100...) or a public @username.
# Set LOG_CHANNEL empty to disable delivery logging.
_log_channel = os.getenv("LOG_CHANNEL", "-1004304801193").strip()
if not _log_channel:
    LOG_CHANNEL = None
elif _log_channel.lstrip("-").isdigit():
    LOG_CHANNEL = int(_log_channel)
else:
    LOG_CHANNEL = _log_channel
UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "")
UPDATE_GROUP = os.getenv("UPDATE_GROUP", "")

# File Settings
FILE_CHANNEL = int(os.getenv("FILE_CHANNEL", "0"))

# Search Settings
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))

# Force Subscription
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "")

# TWO JOIN REQUEST CHANNELS
REQ_CHANNEL1 = -1004393586601
REQ_CHANNEL2 = -1003951518872

# MANUAL JOIN REQUEST LINKS
REQ_LINK1 = os.getenv("REQ_LINK1", "")
REQ_LINK2 = os.getenv("REQ_LINK2", "")
