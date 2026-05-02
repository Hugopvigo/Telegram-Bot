import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AEMET_API_KEY = os.getenv("AEMET_API_KEY")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))
DB_PATH = os.getenv("DB_PATH", "/data/users.db")


def validate():
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not AEMET_API_KEY:
        missing.append("AEMET_API_KEY")
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")
