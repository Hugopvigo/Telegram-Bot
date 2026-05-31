import socket
import time

from app.database import init_db
from app.bot import create_app
from app.scheduler import check_and_notify
from app.config import CHECK_INTERVAL_MINUTES, validate


def _wait_for_network(host="api.telegram.org", retries=12, interval=10):
    """Espera a que DNS resuelva antes de arrancar el bot (Oracle Cloud tarda en inicializar la red Docker)."""
    time.sleep(5)  # Pausa inicial para que la interfaz de red Docker esté lista
    for attempt in range(1, retries + 1):
        try:
            socket.getaddrinfo(host, 443, 0, 1)
            print(f"Red disponible tras {attempt} intento(s).")
            return
        except OSError as e:
            print(f"DNS no disponible (intento {attempt}/{retries}): {e} — retry en {interval}s")
            if attempt == retries:
                raise
            time.sleep(interval)


def main():
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

    print(f"🤖 Bot iniciado. Comprobando alertas cada {CHECK_INTERVAL_MINUTES} min.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
