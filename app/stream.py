import asyncio
from app.rich import send_rich


async def send_loading(chat_id: int, text: str = "Consultando AEMET...") -> object:
    from telegram import Bot
    from app.config import TELEGRAM_BOT_TOKEN
    bot = Bot(TELEGRAM_BOT_TOKEN)
    return await bot.send_message(chat_id=chat_id, text=f"🔍 {text}")


async def delete_loading(message) -> None:
    try:
        await message.delete()
    except Exception:
        pass
