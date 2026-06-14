import httpx
from app.config import TELEGRAM_BOT_TOKEN

TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def send_rich(chat_id: int, html: str, reply_markup=None) -> dict:
    client = await _get_client()
    payload = {
        "chat_id": chat_id,
        "rich_message": {"html": html},
    }
    if reply_markup is not None:
        import json
        payload["reply_markup"] = json.dumps(reply_markup) if not isinstance(reply_markup, str) else reply_markup
    r = await client.post(f"{TG_API}/sendRichMessage", json=payload)
    return r.json()


async def edit_rich(chat_id: int, message_id: int, html: str) -> dict:
    client = await _get_client()
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "rich_message": {"html": html},
    }
    r = await client.post(f"{TG_API}/editMessageText", json=payload)
    return r.json()


async def send_rich_draft(chat_id: int, draft_id: int, html: str) -> dict:
    client = await _get_client()
    payload = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "rich_message": {"html": html},
    }
    r = await client.post(f"{TG_API}/sendRichMessageDraft", json=payload)
    return r.json()


async def close_client():
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
