from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.helpers import escape_markdown
from bot.services import user_service

QR_PATH = Path(__file__).parent.parent / "qr.png"

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🏠 Trang chủ", "🔍 Tìm từ"],
        ["📚 Học từ vựng", "📋 Bộ từ của tôi"],
        ["📊 Báo cáo", "💝 Ủng hộ"],
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


async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset state, clear recent chat history, and re-show start screen."""
    context.user_data.clear()
    chat_id = update.effective_chat.id
    current_msg_id = update.message.message_id
    # Best-effort: delete the last 50 messages (bot + user messages in private chat)
    for msg_id in range(current_msg_id, max(current_msg_id - 50, 0), -1):
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    await start(update, context)


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caption = (
        "💝 <b>Ủng hộ LangGeek Bot</b>\n\n"
        "TECHCOMBANK\n"
        "<b>NGUYEN XUAN HOA</b>\n"
        "<code>1732888888</code>\n\n"
        "Cám ơn đã ủng hộ! 🙏"
    )
    if QR_PATH.exists():
        await update.message.reply_photo(photo=QR_PATH.open("rb"), caption=caption, parse_mode="HTML")
    else:
        await update.message.reply_text(caption, parse_mode="HTML")


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
    context.user_data.clear()
    await update.message.reply_text("🏠 Menu chính:", reply_markup=MAIN_MENU)


def register(app) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(MessageHandler(filters.Regex("^🏠 Trang chủ$"), home))
    app.add_handler(MessageHandler(filters.Regex("^💝 Ủng hộ$"), donate))
