import logging
import socket
import sys
import time

from app.database import init_db
from app.bot import create_app
from app.scheduler import check_and_notify
from app.config import CHECK_INTERVAL_MINUTES, validate

logger = logging.getLogger("tiempobot")


def _wait_for_network(host="api.telegram.org", retries=12, interval=10):
    """Espera a que DNS resuelva antes de arrancar el bot (Oracle Cloud tarda en inicializar la red Docker)."""
    time.sleep(5)  # Pausa inicial para que la interfaz de red Docker esté lista
    for attempt in range(1, retries + 1):
        try:
            socket.getaddrinfo(host, 443, 0, 1)
            logger.info("Red disponible tras %d intento(s).", attempt)
            return
        except OSError as e:
            logger.warning("DNS no disponible (intento %d/%d): %s — retry en %ds", attempt, retries, e, interval)
            if attempt == retries:
                raise
            time.sleep(interval)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    # httpx registra la URL de cada petición, y la de Telegram lleva el token
    logging.getLogger("httpx").setLevel(logging.WARNING)
    validate()
    init_db()
    _wait_for_network()

    app = create_app()

    app.job_queue.run_repeating(
        check_and_notify,
        interval=CHECK_INTERVAL_MINUTES * 60,
        first=30,
        name="aemet_check",
    )

    logger.info("🤖 Bot iniciado. Comprobando alertas cada %d min.", CHECK_INTERVAL_MINUTES)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
