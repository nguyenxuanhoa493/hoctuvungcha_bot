from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler,
)
from bot.services import user_service

WAITING_GOAL = 0


def _accuracy_bar(pct: int, bar_len: int = 10) -> str:
    filled = round(pct / 100 * bar_len)
    return "🟩" * filled + "⬜" * (bar_len - filled)


def _kpi_bar(answered: int, goal: int, bar_len: int = 10) -> str:
    filled = min(round(answered / goal * bar_len), bar_len)
    return "🔵" * filled + "⚪" * (bar_len - filled)


def _report_text(user_id: int) -> str:
    report = user_service.get_daily_report(user_id)
    user = user_service.get_user(user_id)
    stats = user_service.get_stats(user_id)

    today = report["today"]
    answered = today["answered"]
    correct = today["correct"]
    pct = round(correct / answered * 100) if answered else 0
    goal = (user or {}).get("dailyGoal") or 0

    lines = ["📊 <b>Báo cáo hôm nay</b>", ""]

    # KPI progress bar
    if goal:
        kpi_bar = _kpi_bar(answered, goal)
        kpi_pct = min(round(answered / goal * 100), 100)
        lines.append(f"🏆 <b>Mục tiêu ngày</b>: {answered}/{goal} từ  (<b>{kpi_pct}%</b>)")
        lines.append(f"<code>{kpi_bar}</code>")
    else:
        lines.append(f"📝 Đã luyện: <b>{answered}</b> câu hôm nay")

    # Accuracy bar
    lines.append("")
    acc_bar = _accuracy_bar(pct)
    lines.append(f"🎯 <b>Độ chính xác</b>: {correct}/{answered}  (<b>{pct}%</b>)")
    lines.append(f"<code>{acc_bar}</code>")

    # 7-day history
    history = report.get("history", [])
    active_days = [h for h in history if h["answered"] > 0]
    if active_days:
        lines.append("\n📅 <b>7 ngày gần đây</b>")
        for h in reversed(history):
            if h["answered"] == 0:
                continue
            h_pct = round(h["correct"] / h["answered"] * 100)
            bar = _accuracy_bar(h_pct, bar_len=5)
            lines.append(f"  <code>{h['date'][5:]}</code>  {h['answered']} câu  {h_pct}%  <code>{bar}</code>")

    # Overall stats
    total = stats.get("total", 0)
    known = stats.get("known", 0)
    if total:
        lines.append(f"\n📚 Tổng: <b>{total}</b> từ đã học  |  Thuộc: <b>{known}</b> từ")

    return "\n".join(lines)


async def show_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user = user_service.get_user(user_id)
    goal = (user or {}).get("dailyGoal") or 0
    goal_label = f"✏️ Mục tiêu: {goal} từ/ngày  (đổi)" if goal else "🎯 Đặt mục tiêu ngày"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(goal_label, callback_data="report:set_goal")],
        [InlineKeyboardButton("❌ Đóng", callback_data="report:close")],
    ])
    text = _report_text(user_id)
    msg = update.message or (update.callback_query and update.callback_query.message)
    await msg.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    return ConversationHandler.END


async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "report:close":
        await query.delete_message()
        return ConversationHandler.END
    if query.data == "report:set_goal":
        await query.edit_message_text("🎯 Nhập số từ bạn muốn luyện mỗi ngày (ví dụ: 20):")
        return WAITING_GOAL
    return ConversationHandler.END


async def _progress_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


async def receive_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("⚠️ Vui lòng nhập một số nguyên dương.")
        return WAITING_GOAL
    goal = int(text)
    user_service.set_daily_goal(update.effective_user.id, goal)
    await update.message.reply_text(f"✅ Đã đặt mục tiêu <b>{goal} từ/ngày</b>!", parse_mode="HTML")
    await show_report(update, context)
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("progress", show_report),
            MessageHandler(filters.Regex("^📊 Báo cáo$"), show_report),
        ],
        states={
            WAITING_GOAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_goal),
            ],
        },
        fallbacks=[
            MessageHandler(
                filters.Regex("^(🏠 Trang chủ|📚 Học từ vựng|📋 Bộ từ của tôi|🔍 Tìm từ|💝 Ủng hộ)$"),
                _progress_cancel,
            ),
        ],
        name="report_conv",
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(report_callback, pattern=r"^report:"))
