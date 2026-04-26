from app.database import init_db
from app.bot import create_app
from app.scheduler import check_and_notify
from app.config import CHECK_INTERVAL_MINUTES


def main():
    init_db()

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
