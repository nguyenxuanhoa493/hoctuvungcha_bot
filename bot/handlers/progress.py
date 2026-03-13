from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.services import user_service


async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    stats = user_service.get_stats(user_id)
    total = stats.get("total", 0)
    known = stats.get("known", 0)
    learning = stats.get("learning", 0)

    if total == 0:
        await update.message.reply_text(
            "📊 Bạn chưa học từ nào\\. Dùng /study để bắt đầu\\!",
            parse_mode="MarkdownV2",
        )
        return

    pct_known = round(known / total * 100) if total else 0
    bar_len = 20
    filled = round(pct_known / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)

    text = (
        "📊 *Tiến độ học từ vựng*\n\n"
        f"✅ Đã thuộc: *{known}* từ\n"
        f"📖 Đang học: *{learning}* từ\n"
        f"📝 Tổng đã gặp: *{total}* từ\n\n"
        f"`[{bar}]` {pct_known}%"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def register(app) -> None:
    app.add_handler(CommandHandler("progress", progress))
    from telegram.ext import MessageHandler, filters as f
    app.add_handler(MessageHandler(f.Regex("^📊 Tiến độ$"), progress))
