# 🌤️ TiempoBot

Bot de Telegram para recibir alertas meteorológicas de la **AEMET** (Agencia Estatal de Meteorología) en tiempo real. Suscríbete a tu provincia y recibe notificaciones automáticas cuando se emitan avisos.

---

## ✨ Características

- 🔔 **Notificaciones automáticas** — El bot consulta la API de AEMET periódicamente y te envía alertas nuevas
- 🗺️ **52 provincias españolas** — Cobertura completa incluyendo Ceuta y Melilla
- 🎹 **Teclado interactivo** — Selección de provincia con botones en Telegram
- 🎨 **Emojis por severidad** — 🟢 Moderado, 🟡 Importante, 🟠 Naranja, 🔴 Rojo/Extremo
- 🛡️ **Deduplicación** — Nunca recibes la misma alerta dos veces
- 🧹 **Limpieza automática** — Alerts antiguas purgadas tras 7 días
- 🐳 **Docker ready** — Despliegue con un solo comando

---

## 📁 Estructura del proyecto

```
TiempoBot/
├── run.py              # 🚀 Punto de entrada
├── requirements.txt    # 📦 Dependencias Python
├── Dockerfile          # 🐳 Imagen Docker
├── docker-compose.yml  # 🐳 Composición Docker
├── .env.example        # 🔑 Plantilla de variables de entorno
├── .gitignore
└── app/
    ├── __init__.py     # 📦 Paquete Python
    ├── main.py         # 🧠 Orquestador: init DB, bot, scheduler, polling
    ├── config.py       # ⚙️ Lectura de variables de entorno
    ├── bot.py          # 🤖 Handlers de comandos de Telegram
    ├── aemet.py        # 🌦️ Cliente API AEMET: códigos, fetch, formateo
    ├── database.py     # 💾 SQLite: usuarios, alertas enviadas, CRUD
    └── scheduler.py    # ⏰ Job periódico: fetch + notificación + dedup
```

---

## 🛠️ Tech Stack

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Bot Framework | python-telegram-bot | 21.3 |
| HTTP Client | httpx | 0.27.0 |
| Scheduler | APScheduler | 3.10.4 |
| Base de datos | SQLite3 | stdlib |
| Contenedor | Docker + Docker Compose | — |
| API externa | AEMET OpenData | REST |

---

## 🤖 Comandos del bot

| Comando | Descripción |
|---|---|
| `/start [provincia]` | Mensaje de bienvenida; suscripción opcional directa |
| `/suscribir <provincia>` | Suscribirse a alertas de una provincia (teclado interactivo sin argumento) |
| `/provincias` | Ver las 52 provincias disponibles |
| `/alertas` | Consultar alertas activas de tu provincia |
| `/estado` | Ver estado de tu suscripción |
| `/cancelar` | Cancelar suscripción |

---

## ⚙️ Variables de entorno

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ Sí | — | Token del bot desde [@BotFather](https://t.me/BotFather) |
| `AEMET_API_KEY` | ✅ Sí | — | API key desde [AEMET OpenData](https://opendata.aemet.es/) |
| `CHECK_INTERVAL_MINUTES` | ❌ No | `10` | Intervalo (minutos) entre consultas a AEMET |
| `DB_PATH` | ❌ No | `/data/users.db` | Ruta de la base de datos SQLite |

---

## 🚀 Instalación y uso

### Local

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves

# Ejecutar
python run.py
```

### Docker

```bash
# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves

# Construir e iniciar
docker compose up -d

# Ver logs
docker compose logs -f

# Detener
docker compose down
```

---

## 💾 Esquema de base de datos

**`users`** — Suscripciones de usuarios

| Columna | Tipo | Descripción |
|---|---|---|
| `chat_id` | INTEGER (PK) | ID del chat de Telegram |
| `provincia_code` | TEXT | Código de provincia AEMET |
| `provincia_name` | TEXT | Nombre de la provincia |

**`sent_alerts`** — Alertas ya enviadas (deduplicación)

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER (PK) | Autoincremental |
| `chat_id` | INTEGER | ID del chat |
| `alert_id` | TEXT | Identificador único de la alerta |
| `sent_at` | TIMESTAMP | Fecha de envío |

> Constraint `UNIQUE(chat_id, alert_id)` evita duplicados.

---

## 🔑 Obtener credenciales

1. **Telegram Bot Token** — Habla con [@BotFather](https://t.me/BotFather) en Telegram y crea un nuevo bot
2. **AEMET API Key** — Regístrate en [AEMET OpenData](https://opendata.aemet.es/) y solicita tu clave de API

---

## 📄 Licencia

Este proyecto está bajo la licencia [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

Puedes usar, modificar y distribuir este proyecto libremente, dando crédito al autor original.
