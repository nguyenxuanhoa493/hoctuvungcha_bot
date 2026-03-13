from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from bot.services import vocab_service, user_service


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    query_text = " ".join(args).strip() if args else ""

    if not query_text:
        await update.message.reply_text(
            "🔍 Cách dùng: `/search <từ cần tìm>`\nVí dụ: `/search hello`",
            parse_mode="Markdown",
        )
        return

    results = vocab_service.search(query_text)
    if not results:
        await update.message.reply_text(f"❌ Không tìm thấy từ nào khớp với *{query_text}*.", parse_mode="Markdown")
        return

    await update.message.reply_text(
        f"🔍 Kết quả cho *{query_text}* ({len(results)} từ):",
        parse_mode="Markdown",
    )

    for v in results[:5]:
        await _send_vocab_detail(update, context, int(v["sqlId"]))


async def _send_vocab_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, vocab_id: int) -> None:
    vocab = vocab_service.get_vocab_detail(vocab_id)
    if not vocab:
        return

    lines = [
        f"🔤 *{vocab['word']}*",
        f"📢 /{vocab.get('pronunciationIpa', vocab.get('pronunciation', ''))}/"
        if vocab.get("pronunciationIpa") or vocab.get("pronunciation") else "",
        f"🇻🇳 {vocab.get('meaningVi', '')}",
        f"📂 {vocab.get('levelTitle', '')} › {vocab.get('subcatTitle', '')}",
    ]
    if vocab.get("synonyms"):
        lines.append(f"🔗 _{vocab['synonyms']}_")

    examples = vocab.get("examples", [])[:2]
    if examples:
        lines.append("\n*Ví dụ:*")
        for ex in examples:
            lines.append(f"  • {ex['exampleEn']}")
            if ex.get("exampleVi"):
                lines.append(f"    _{ex['exampleVi']}_")

    text = "\n".join(l for l in lines if l)

    # Build add-to-set buttons
    sets = user_service.list_custom_sets(update.effective_user.id)
    buttons = []
    if sets:
        buttons = [
            [InlineKeyboardButton(f"➕ Thêm vào: {s['name']}", callback_data=f"search_add:{s['_id']}:{vocab_id}")]
            for s in sets[:3]
        ]
    keyboard = InlineKeyboardMarkup(buttons) if buttons else None

    if vocab.get("imageUrl"):
        await update.message.reply_photo(
            photo=vocab["imageUrl"],
            caption=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_search_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    set_id = parts[1]
    vocab_id = int(parts[2])
    user_service.add_word_to_set(set_id, vocab_id)
    await query.answer("✅ Đã thêm vào bộ từ!", show_alert=False)


async def search_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.replace("🔍 Tìm từ", "").strip()
    if not text:
        await update.message.reply_text(
            "🔍 Nhập từ cần tìm: `/search <từ>`", parse_mode="Markdown"
        )
        return
    context.args = text.split()
    await search(update, context)


def register(app) -> None:
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CommandHandler("search", search))
    app.add_handler(MessageHandler(filters.Regex("^🔍 Tìm từ$"), search_from_message))
    app.add_handler(CallbackQueryHandler(handle_search_add, pattern=r"^search_add:"))
