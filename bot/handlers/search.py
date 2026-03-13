from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler,
)
from bot.services import vocab_service, user_service

WAITING_QUERY = 0


async def ask_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Triggered by /search command or 🔍 Tìm từ button."""
    args = context.args
    if args:
        await _do_search(update, context, " ".join(args).strip())
        return ConversationHandler.END

    from telegram import ForceReply
    await update.message.reply_text(
        "🔍 Nhập từ cần tìm:",
        reply_markup=ForceReply(input_field_placeholder="Gõ từ tiếng Anh..."),
    )
    return WAITING_QUERY


async def receive_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query_text = update.message.text.strip()
    await _do_search(update, context, query_text)
    return ConversationHandler.END


async def _do_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str) -> None:
    results = vocab_service.search(query_text)
    if not results:
        await update.message.reply_text(
            f"❌ Không tìm thấy từ nào khớp với <b>{query_text}</b>.", parse_mode="HTML"
        )
        return

    buttons = []
    for v in results[:10]:
        word = v.get("word", "")
        meaning = v.get("meaningVi", "")
        label = f"{word}  —  {meaning[:20]}{'…' if len(meaning) > 20 else ''}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"search_pick:{int(v['sqlId'])}")])

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"🔍 <b>{query_text}</b> — {len(results)} kết quả:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def handle_search_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detail for a picked word."""
    query = update.callback_query
    await query.answer()
    vocab_id = int(query.data.split(":")[1])
    await _send_vocab_detail(query, context, vocab_id)


async def _send_vocab_detail(source, context: ContextTypes.DEFAULT_TYPE, vocab_id: int) -> None:
    """source can be Update.message or CallbackQuery."""
    vocab = vocab_service.get_vocab_detail(vocab_id)
    if not vocab:
        return

    ipa = vocab.get("pronunciationIpa") or vocab.get("pronunciation") or ""
    lines = [f"🔤 <b>{vocab['word']}</b>"]
    if ipa:
        lines.append(f"📢 <code>/{ipa}/</code>")
    lines.append(f"🇻🇳 {vocab.get('meaningVi', '')}")
    lines.append(f"📂 {vocab.get('levelTitle', '')} › {vocab.get('subcatTitle', '')}")
    if vocab.get("synonyms"):
        lines.append(f"🔗 <i>{vocab['synonyms']}</i>")

    examples = vocab.get("examples", [])[:2]
    if examples:
        lines.append("\n<b>Ví dụ:</b>")
        for ex in examples:
            lines.append(f"  • {ex['exampleEn']}")
            if ex.get("exampleVi"):
                lines.append(f"    <i>{ex['exampleVi']}</i>")

    text = "\n".join(l for l in lines if l)

    # Determine user_id
    user_id = source.from_user.id if hasattr(source, "from_user") else source.message.chat_id
    sets = user_service.list_custom_sets(user_id)
    add_buttons = [
        [InlineKeyboardButton(f"➕ {s['name']}", callback_data=f"search_add:{s['_id']}:{vocab_id}")]
        for s in (sets or [])[:3]
    ]
    keyboard = InlineKeyboardMarkup(add_buttons) if add_buttons else None

    # Send audio if available
    audio_url = vocab.get("audioUrl")
    chat_id = source.message.chat_id if hasattr(source, "message") else source.chat_id
    if audio_url:
        try:
            await context.bot.send_voice(chat_id, voice=audio_url)
        except Exception:
            pass

    if vocab.get("imageUrl"):
        await context.bot.send_photo(
            chat_id,
            photo=vocab["imageUrl"],
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        await context.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)


async def handle_search_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    set_id = parts[1]
    vocab_id = int(parts[2])
    user_service.add_word_to_set(set_id, vocab_id)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.answer("✅ Đã thêm vào bộ từ!", show_alert=True)


async def _search_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", ask_search),
            MessageHandler(filters.Regex("^🔍 Tìm từ$"), ask_search),
        ],
        states={
            WAITING_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_query),
            ],
        },
        fallbacks=[
            CommandHandler("menu", _search_cancel),
            MessageHandler(
                filters.Regex("^(📚 Học từ vựng|📋 Bộ từ của tôi|📊 Báo cáo|🔍 Tìm từ)$"),
                _search_cancel,
            ),
        ],
        name="search_conv",
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(handle_search_pick, pattern=r"^search_pick:"))
    app.add_handler(CallbackQueryHandler(handle_search_add, pattern=r"^search_add:"))



async def ask_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Triggered by /search command or 🔍 Tìm từ button."""
    args = context.args
    # If command has inline args (e.g. /search hello), search immediately
    if args:
        await _do_search(update, context, " ".join(args).strip())
        return ConversationHandler.END

    from telegram import ForceReply
    await update.message.reply_text(
        "🔍 Nhập từ cần tìm:",
        reply_markup=ForceReply(input_field_placeholder="Gõ từ tiếng Anh..."),
    )
    return WAITING_QUERY


async def receive_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query_text = update.message.text.strip()
    await _do_search(update, context, query_text)
    return ConversationHandler.END


async def _do_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str) -> None:
    results = vocab_service.search(query_text)
    if not results:
        await update.message.reply_text(
            f"❌ Không tìm thấy từ nào khớp với *{query_text}*.", parse_mode="Markdown"
        )
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
    await query.edit_message_reply_markup(reply_markup=None)
    await query.answer("✅ Đã thêm vào bộ từ!", show_alert=True)


async def _search_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", ask_search),
            MessageHandler(filters.Regex("^🔍 Tìm từ$"), ask_search),
        ],
        states={
            WAITING_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_query),
            ],
        },
        fallbacks=[
            CommandHandler("menu", _search_cancel),
            MessageHandler(
                filters.Regex("^(📚 Học từ vựng|📋 Bộ từ của tôi|📊 Báo cáo|🔍 Tìm từ)$"),
                _search_cancel,
            ),
        ],
        name="search_conv",
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(handle_search_add, pattern=r"^search_add:"))
