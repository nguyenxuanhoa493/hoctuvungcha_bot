import asyncio
import logging
import traceback
from telegram import Update
from telegram.ext import Application, ContextTypes
from bot.config import BOT_TOKEN, WEBHOOK_URL, PORT
from bot.handlers import start, study, myset, progress, search

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Exception while handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Đã xảy ra lỗi, vui lòng thử lại."
        )


def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    start.register(app)
    study.register(app)
    myset.register(app)
    progress.register(app)
    search.register(app)
    app.add_error_handler(error_handler)
    return app


def main() -> None:
    app = build_app()

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
    # Explicitly create event loop for compatibility with Python 3.12+
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        main()
    finally:
        loop.close()
