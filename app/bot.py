from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from app.config import TELEGRAM_BOT_TOKEN
from app import database as db
from app.aemet import (
    PROVINCIAS,
    search_provincia,
    get_alertas_provincia,
    format_alerta,
    PROVINCIA_CODES,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        query = " ".join(args)
        codigo = search_provincia(query)
        if codigo:
            nombre = PROVINCIA_CODES[codigo]
            db.add_user(update.effective_chat.id, codigo, nombre)
            await update.message.reply_text(
                f"✅ Te has suscrito a las alertas de *{nombre}*.\n"
                f"Recibirás notificaciones cuando haya alertas activas.\n\n"
                f"Usa /alertas para ver las alertas actuales.\n"
                f"Usa /cancelar para darte de baja.",
                parse_mode="Markdown",
            )
            return
        await update.message.reply_text(
            f"❌ No encontré la provincia '{query}'.\n"
            f"Usa /provincias para ver las disponibles.",
        )
        return

    await update.message.reply_text(
        "🌤 *AlertasMeteo Bot*\n\n"
        "Te notifico cuando AEMET emita alertas meteorológicas en tu provincia.\n\n"
        "Comandos:\n"
        "/suscribir <provincia> — Suscribirte a alertas\n"
        "/provincias — Ver provincias disponibles\n"
        "/alertas — Ver alertas actuales de tu provincia\n"
        "/estado — Ver tu suscripción\n"
        "/cancelar — Cancelar suscripción",
        parse_mode="Markdown",
    )


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
        await update.message.reply_text(
            f"❌ No encontré la provincia '{query}'. Usa /provincias para ver las disponibles."
        )
        return

    nombre = PROVINCIA_CODES[codigo]
    db.add_user(update.effective_chat.id, codigo, nombre)
    await update.message.reply_text(
        f"✅ Suscrito a alertas de *{nombre}*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


async def provincias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombres = sorted(PROVINCIAS.keys())
    text = "🗺 *Provincias disponibles:*\n\n" + "\n".join(
        f"• {n}" for n in nombres
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_chat.id)
    if not user:
        await update.message.reply_text(
            "❌ No estás suscrito. Usa /suscribir <provincia>"
        )
        return

    alertas_list = get_alertas_provincia(user["provincia_code"])
    if not alertas_list:
        await update.message.reply_text(
            f"✅ No hay alertas activas para {user['provincia_name']}"
        )
        return

    messages = []
    for a in alertas_list:
        messages.append(format_alerta(a))

    full_text = f"⚠ Alertas para *{user['provincia_name']}*:\n\n" + "\n\n---\n\n".join(messages)
    for chunk in _split_message(full_text):
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_chat.id)
    if not user:
        await update.message.reply_text("No estás suscrito a ninguna provincia.")
        return
    await update.message.reply_text(
        f"📍 Suscrito a: *{user['provincia_name']}*\n"
        f"Usa /alertas para ver alertas actuales.",
        parse_mode="Markdown",
    )


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_chat.id)
    if not user:
        await update.message.reply_text("No estás suscrito.")
        return
    db.remove_user(update.effective_chat.id)
    await update.message.reply_text(
        f"❌ Suscripción a {user['provincia_name']} cancelada.",
        reply_markup=ReplyKeyboardRemove(),
    )


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
    await update.message.reply_text(
        f"✅ Suscrito a alertas de *{nombre}*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


def _split_message(text: str, limit: int = 4096) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts


def create_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("suscribir", suscribir))
    app.add_handler(CommandHandler("provincias", provincias))
    app.add_handler(CommandHandler("alertas", alertas))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_provincia_text))

    return app
