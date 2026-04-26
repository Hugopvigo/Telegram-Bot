import os

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
AEMET_API_KEY = os.environ["AEMET_API_KEY"]
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "10"))
DB_PATH = os.environ.get("DB_PATH", "/data/users.db")
