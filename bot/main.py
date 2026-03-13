import logging
from telegram.ext import Application
from bot.config import BOT_TOKEN, WEBHOOK_URL, PORT
from bot.handlers import start, study, myset, progress, search

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# Suppress noisy httpx/httpcore debug logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    start.register(app)
    study.register(app)
    myset.register(app)
    progress.register(app)
    search.register(app)

    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{WEBHOOK_URL}/webhook",
            url_path="/webhook",
        )
    else:
        logging.info("No WEBHOOK_URL set — running in polling mode.")
        app.run_polling()


if __name__ == "__main__":
    main()
