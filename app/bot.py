from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from app.config import TELEGRAM_BOT_TOKEN
from app import database as db
from app.rich import send_rich
from app.aemet import (
    PROVINCIAS,
    search_provincia,
    get_alertas_provincia,
    get_alertas_nacional,
    PROVINCIA_CODES,
    MIN_NOTIFY_SEVERITY,
    format_alerta_rich_full,
    format_provincias_rich,
    format_start_rich,
    format_estado_rich,
    format_nacional_rich,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        query = " ".join(args)
        codigo = search_provincia(query)
        if codigo:
            nombre = PROVINCIA_CODES[codigo]
            db.add_user(update.effective_chat.id, codigo, nombre)
            html = (
                f"<h2>✅ Suscrito correctamente</h2>\n"
                f"<p>Recibirás alertas de <b>{nombre}</b> cuando AEMET emita avisos.</p>\n"
                f"<footer>Usa /alertas para consultar · /cancelar para darte de baja</footer>"
            )
            await send_rich(update.effective_chat.id, html)
            return
        html = (
            f"<h2>❌ Provincia no encontrada</h2>\n"
            f"<p>No encontré '<b>{query}</b>'.</p>\n"
            f"<p>Usa <code>/provincias</code> para ver las disponibles.</p>"
        )
        await send_rich(update.effective_chat.id, html)
        return

    await send_rich(update.effective_chat.id, format_start_rich())


async def suscribir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        prov_list = sorted(PROVINCIAS.keys())
        keyboard = []
        for i in range(0, len(prov_list), 3):
            row = prov_list[i : i + 3]
            keyboard.append(row)
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Selecciona tu provincia o escríbela:",
            reply_markup=reply_markup,
        )
        return

    query = " ".join(context.args)
    codigo = search_provincia(query)
    if not codigo:
        html = (
            f"<h2>❌ Provincia no encontrada</h2>\n"
            f"<p>No encontré '<b>{query}</b>'. Usa <code>/provincias</code> para ver las disponibles.</p>"
        )
        await send_rich(update.effective_chat.id, html)
        return

    nombre = PROVINCIA_CODES[codigo]
    db.add_user(update.effective_chat.id, codigo, nombre)
    html = (
        f"<h2>✅ Suscrito correctamente</h2>\n"
        f"<p>Recibirás alertas de <b>{nombre}</b> cuando AEMET emita avisos.</p>\n"
        f"<footer>Usa /alertas para consultar · /cancelar para darte de baja</footer>"
    )
    await send_rich(update.effective_chat.id, html, reply_markup=ReplyKeyboardRemove())


async def provincias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_rich(update.effective_chat.id, format_provincias_rich())


async def alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_chat.id)
    if not user:
        html = (
            "<h2>❌ No suscrito</h2>\n"
            "<p>No estás suscrito a ninguna provincia.</p>\n"
            "<p>Usa <code>/suscribir</code> para comenzar.</p>"
        )
        await send_rich(update.effective_chat.id, html)
        return

    loading = await update.message.reply_text("🔍 Consultando alertas de AEMET...")

    alertas_list = get_alertas_provincia(user["provincia_code"], min_severity=MIN_NOTIFY_SEVERITY)
    if not alertas_list:
        html = f"<h2>✅ Sin alertas</h2>\n<p>No hay alertas activas para <b>{user['provincia_name']}</b>.</p>"
        await send_rich(update.effective_chat.id, html)
        await loading.delete()
        return

    html = format_alerta_rich_full(user["provincia_name"], alertas_list)
    await send_rich(update.effective_chat.id, html)
    await loading.delete()


async def alertas_nacionales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loading = await update.message.reply_text("🔍 Consultando alertas nacionales...")

    alertas_list = get_alertas_nacional(min_severity=MIN_NOTIFY_SEVERITY)
    html = format_nacional_rich(alertas_list)
    await send_rich(update.effective_chat.id, html)
    await loading.delete()


async def clima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    html = (
        "<h2>🌤 Consulta el tiempo</h2>\n"
        "<p>Puedes consultar el tiempo en la web <a href=\"https://tiempo.hugoperezvigo.es/\">tiempo.hugoperezvigo.es</a></p>\n"
        "<p>O descargarte la app desde <a href=\"https://hugopvigo.github.io/Tiempo/\">hugopvigo.github.io/Tiempo</a></p>\n"
        "<footer>📡 Fuente: AEMET</footer>"
    )
    await send_rich(update.effective_chat.id, html)


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_chat.id)
    if not user:
        html = "<p>No estás suscrito a ninguna provincia.</p>"
        await send_rich(update.effective_chat.id, html)
        return
    await send_rich(update.effective_chat.id, format_estado_rich(user["provincia_name"]))


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_chat.id)
    if not user:
        html = "<p>No estás suscrito.</p>"
        await send_rich(update.effective_chat.id, html)
        return
    db.remove_user(update.effective_chat.id)
    html = (
        f"<h2>❌ Suscripción cancelada</h2>\n"
        f"<p>No recibirás más alertas de <b>{user['provincia_name']}</b>.</p>\n"
        f"<p>Usa <code>/suscribir</code> si quieres volver a suscribirte.</p>"
    )
    await send_rich(update.effective_chat.id, html, reply_markup=ReplyKeyboardRemove())


async def handle_provincia_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text in PROVINCIAS:
        codigo = PROVINCIAS[update.message.text]
        nombre = update.message.text
    else:
        codigo = search_provincia(update.message.text)
        if not codigo:
            return
        nombre = PROVINCIA_CODES[codigo]

    db.add_user(update.effective_chat.id, codigo, nombre)
    html = (
        f"<h2>✅ Suscrito correctamente</h2>\n"
        f"<p>Recibirás alertas de <b>{nombre}</b> cuando AEMET emita avisos.</p>\n"
        f"<footer>Usa /alertas para consultar · /cancelar para darte de baja</footer>"
    )
    await send_rich(update.effective_chat.id, html, reply_markup=ReplyKeyboardRemove())


def create_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("suscribir", suscribir))
    app.add_handler(CommandHandler("provincias", provincias))
    app.add_handler(CommandHandler("alertas", alertas))
    app.add_handler(CommandHandler("alertas_nacionales", alertas_nacionales))
    app.add_handler(CommandHandler("clima", clima))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_provincia_text))

    commands = [
        BotCommand("start", "Iniciar el bot"),
        BotCommand("suscribir", "Suscribirse a una provincia"),
        BotCommand("provincias", "Ver lista de provincias"),
        BotCommand("alertas", "Alertas meteorológicas"),
        BotCommand("alertas_nacionales", "Alertas a nivel nacional"),
        BotCommand("clima", "Consulta el tiempo"),
        BotCommand("estado", "Estado del bot"),
        BotCommand("cancelar", "Cancelar suscripción"),
    ]
    app.bot.set_my_commands(commands)

    return app
