import asyncio
from collections import defaultdict
from telegram.ext import ContextTypes
from app import database as db
from app.rich import send_rich
from app.aemet import (
    get_alertas_provincia,
    format_alerta_rich,
    merge_alertas,
    clear_tar_cache,
    MIN_NOTIFY_SEVERITY,
)


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    clear_tar_cache()

    users = db.get_all_users()
    if not users:
        return

    provincia_users: dict[str, list[int]] = defaultdict(list)
    for u in users:
        provincia_users[u["provincia_code"]].append(u["chat_id"])

    for codigo, chat_ids in provincia_users.items():
        alertas = get_alertas_provincia(codigo, min_severity=MIN_NOTIFY_SEVERITY)
        if not alertas:
            continue

        alertas = merge_alertas(alertas)

        for alerta in alertas:
            alert_id = alerta.get("dedup_key") or alerta.get("identifier", alerta.get("id", ""))
            if not alert_id:
                continue

            html = format_alerta_rich(alerta)

            for chat_id in chat_ids:
                if db.is_alert_sent(chat_id, alert_id):
                    continue
                try:
                    await send_rich(chat_id, html)
                    db.mark_alert_sent(chat_id, alert_id)
                except Exception as e:
                    print(f"Error enviando a {chat_id}: {e}")

        await asyncio.sleep(1)

    db.cleanup_old_alerts()
