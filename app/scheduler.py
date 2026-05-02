import asyncio
from collections import defaultdict
from telegram.ext import ContextTypes
from app import database as db
from app.aemet import get_alertas_provincia, format_alerta, clear_tar_cache


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    clear_tar_cache()

    users = db.get_all_users()
    if not users:
        return

    provincia_users: dict[str, list[int]] = defaultdict(list)
    for u in users:
        provincia_users[u["provincia_code"]].append(u["chat_id"])

    for codigo, chat_ids in provincia_users.items():
        alertas = get_alertas_provincia(codigo)
        if not alertas:
            continue

        for alerta in alertas:
            alert_id = alerta.get("identifier", alerta.get("id", ""))
            if not alert_id:
                continue

            text = format_alerta(alerta)

            for chat_id in chat_ids:
                if db.is_alert_sent(chat_id, alert_id):
                    continue
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode="Markdown",
                    )
                    db.mark_alert_sent(chat_id, alert_id)
                except Exception as e:
                    print(f"Error enviando a {chat_id}: {e}")

        await asyncio.sleep(1)

    db.cleanup_old_alerts()
