from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from telegram.helpers import escape_markdown
from bot.services import user_service

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📚 Học từ vựng", "📋 Bộ từ của tôi"],
        ["📊 Báo cáo", "🔍 Tìm từ"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_service.upsert_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    safe_name = escape_markdown(user.first_name, version=2)
    await update.message.reply_text(
        f"👋 Xin chào *{safe_name}*\\!\n\n"
        "Chào mừng bạn đến với *LangGeek Bot* 🎓\n"
        "Tôi sẽ giúp bạn học từ vựng tiếng Anh hiệu quả\\.\n\n"
        "Chọn một chức năng bên dưới để bắt đầu:",
        parse_mode="MarkdownV2",
        reply_markup=MAIN_MENU,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *Hướng dẫn sử dụng*\n\n"
        "• /study — Chọn chủ đề và bắt đầu học\n"
        "• /myset — Quản lý bộ từ cá nhân\n"
        "• /progress — Xem báo cáo học tập\n"
        "• /search \\<từ\\> — Tìm kiếm từ vựng\n"
        "• /menu — Quay về menu chính\n"
        "• /stop — Dừng phiên học\n\n"
        "3 chế độ học:\n"
        "🃏 *Flashcard* — Biết / Chưa biết\n"
        "🎯 *Trắc nghiệm* — Chọn 1 trong 4 đáp án\n"
        "⌨️ *Gõ đáp án* — Gõ từ tiếng Anh từ gợi ý",
        parse_mode="MarkdownV2",
    )


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show main menu — works from anywhere, ends any active conversation."""
    context.user_data.clear()
    await update.message.reply_text(
        "🏠 Menu chính:",
        reply_markup=MAIN_MENU,
    )


def register(app) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
