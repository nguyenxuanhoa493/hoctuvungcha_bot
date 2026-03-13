"""Study flow: choose source → mode → study session."""
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters,
)
from bot.services import vocab_service

# ConversationHandler states
(
    CHOOSE_SOURCE,
    CHOOSE_LEVEL,
    CHOOSE_SUBCAT,
    CHOOSE_CUSTOM_SET,
    CHOOSE_MODE,
    STUDYING,
) = range(6)

# Study modes
MODE_FLASHCARD = "flashcard"
MODE_QUIZ = "quiz"
MODE_TYPING = "typing"

ITEMS_PER_PAGE = 8


def _level_keyboard(levels: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{lv['title']}  ({lv.get('subcatCount', '')} chủ đề)" if lv.get('subcatCount') else lv['title'],
            callback_data=f"level:{int(lv['sqlId'])}"
        )]
        for lv in levels
    ]
    buttons.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_source")])
    return InlineKeyboardMarkup(buttons)


def _subcat_keyboard(subcats: list[dict], page: int = 0) -> InlineKeyboardMarkup:
    start = page * ITEMS_PER_PAGE
    chunk = subcats[start: start + ITEMS_PER_PAGE]
    buttons = [
        [InlineKeyboardButton(s["title"], callback_data=f"subcat:{int(s['sqlId'])}")]
        for s in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Trước", callback_data=f"subcat_page:{page - 1}"))
    if start + ITEMS_PER_PAGE < len(subcats):
        nav.append(InlineKeyboardButton("Tiếp ▶️", callback_data=f"subcat_page:{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_levels")])
    return InlineKeyboardMarkup(buttons)


def _mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 Flashcard", callback_data=f"mode:{MODE_FLASHCARD}")],
        [InlineKeyboardButton("🎯 Trắc nghiệm", callback_data=f"mode:{MODE_QUIZ}")],
        [InlineKeyboardButton("⌨️ Gõ đáp án", callback_data=f"mode:{MODE_TYPING}")],
        [InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_subcat")],
    ])


async def study_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Chọn Level / Chủ đề", callback_data="source:level")],
        [InlineKeyboardButton("📋 Bộ từ của tôi", callback_data="source:custom")],
        [InlineKeyboardButton("❌ Huỷ", callback_data="cancel")],
    ])
    msg = update.message or update.callback_query.message
    await msg.reply_text("📚 *Chọn nguồn từ vựng để học:*", parse_mode="Markdown", reply_markup=keyboard)
    return CHOOSE_SOURCE


async def choose_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Đã huỷ.")
        return ConversationHandler.END

    if data == "source:level":
        levels = vocab_service.get_levels_with_subcat_count()
        await query.edit_message_text(
            "📂 *Chọn Level:*", parse_mode="Markdown",
            reply_markup=_level_keyboard(levels)
        )
        return CHOOSE_LEVEL

    if data == "source:custom":
        from bot.services import user_service
        sets = user_service.list_custom_sets(query.from_user.id)
        if not sets:
            await query.edit_message_text(
                "Bạn chưa có bộ từ nào\\. Dùng /myset để tạo\\.",
                parse_mode="MarkdownV2",
            )
            return ConversationHandler.END
        buttons = [
            [InlineKeyboardButton(s["name"], callback_data=f"custom_set:{s['_id']}")]
            for s in sets
        ]
        buttons.append([InlineKeyboardButton("❌ Huỷ", callback_data="cancel")])
        await query.edit_message_text(
            "📋 *Chọn bộ từ:*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return CHOOSE_CUSTOM_SET
    return CHOOSE_SOURCE


async def choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data in ("cancel", "back_to_source"):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Chọn Level / Chủ đề", callback_data="source:level")],
            [InlineKeyboardButton("📋 Bộ từ của tôi", callback_data="source:custom")],
            [InlineKeyboardButton("❌ Huỷ", callback_data="cancel")],
        ])
        await query.edit_message_text(
            "📚 *Chọn nguồn từ vựng để học:*", parse_mode="Markdown", reply_markup=keyboard
        )
        return CHOOSE_SOURCE

    if data.startswith("level:"):
        level_id = int(data.split(":")[1])
        subcats = vocab_service.get_subcategories(level_id)
        context.user_data["subcats"] = subcats
        context.user_data["subcat_page"] = 0
        await query.edit_message_text(
            "📑 *Chọn chủ đề:*", parse_mode="Markdown",
            reply_markup=_subcat_keyboard(subcats, 0)
        )
        return CHOOSE_SUBCAT

    return CHOOSE_LEVEL


async def choose_subcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Đã huỷ.")
        return ConversationHandler.END

    if data == "back_to_levels":
        levels = vocab_service.get_levels()
        await query.edit_message_text(
            "📂 *Chọn Level:*", parse_mode="Markdown",
            reply_markup=_level_keyboard(levels)
        )
        return CHOOSE_LEVEL

    if data.startswith("subcat_page:"):
        page = int(data.split(":")[1])
        context.user_data["subcat_page"] = page
        subcats = context.user_data.get("subcats", [])
        await query.edit_message_reply_markup(reply_markup=_subcat_keyboard(subcats, page))
        return CHOOSE_SUBCAT

    if data.startswith("subcat:"):
        subcat_id = int(data.split(":")[1])
        vocab_list = vocab_service.get_vocab_list(subcat_id=subcat_id)
        if not vocab_list:
            await query.edit_message_text("⚠️ Chủ đề này chưa có từ vựng.")
            return ConversationHandler.END
        context.user_data["vocab_list"] = vocab_list
        context.user_data["vocab_index"] = 0
        await query.edit_message_text(
            f"✅ Đã chọn chủ đề với *{len(vocab_list)} từ*\\.\n\n*Chọn chế độ học:*",
            parse_mode="MarkdownV2",
            reply_markup=_mode_keyboard()
        )
        return CHOOSE_MODE
    return CHOOSE_SUBCAT


async def choose_custom_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Đã huỷ.")
        return ConversationHandler.END

    if data.startswith("custom_set:"):
        from bot.services import user_service
        set_id = data.split(":", 1)[1]
        custom_set = user_service.get_custom_set(set_id)
        if not custom_set or not custom_set.get("vocabIds"):
            await query.edit_message_text("⚠️ Bộ từ này trống hoặc không tìm thấy.")
            return ConversationHandler.END
        vocab_list = vocab_service.get_vocab_list(vocab_ids=custom_set["vocabIds"])
        if not vocab_list:
            await query.edit_message_text("⚠️ Không tìm thấy từ nào trong bộ này.")
            return ConversationHandler.END
        random.shuffle(vocab_list)
        context.user_data["vocab_list"] = vocab_list
        context.user_data["vocab_index"] = 0
        await query.edit_message_text(
            f"✅ Bộ *{custom_set['name']}* — *{len(vocab_list)} từ*\\.\n\n*Chọn chế độ học:*",
            parse_mode="MarkdownV2",
            reply_markup=_mode_keyboard()
        )
        return CHOOSE_MODE
    return CHOOSE_CUSTOM_SET


async def choose_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data in ("cancel", "back_to_subcat"):
        subcats = context.user_data.get("subcats", [])
        if subcats:
            page = context.user_data.get("subcat_page", 0)
            await query.edit_message_text(
                "📑 *Chọn chủ đề:*", parse_mode="Markdown",
                reply_markup=_subcat_keyboard(subcats, page)
            )
            return CHOOSE_SUBCAT
        await query.edit_message_text("❌ Đã huỷ.")
        return ConversationHandler.END

    if data.startswith("mode:"):
        mode = data.split(":")[1]
        context.user_data["mode"] = mode
        context.user_data["vocab_index"] = 0
        await query.edit_message_text("✅ Bắt đầu học\\! Gõ /stop để dừng\\.", parse_mode="MarkdownV2")

        if mode == MODE_FLASHCARD:
            from bot.handlers.flashcard import send_flashcard
            await send_flashcard(update, context)
        elif mode == MODE_QUIZ:
            from bot.handlers.quiz import send_quiz
            await send_quiz(update, context)
        elif mode == MODE_TYPING:
            from bot.handlers.typing import send_typing_prompt
            await send_typing_prompt(update, context)
        return STUDYING
    return CHOOSE_MODE


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("⏹ Đã dừng phiên học.")
    return ConversationHandler.END


async def cancel_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fallback: menu button pressed while in study conv → dispatch to correct handler."""
    context.user_data.clear()
    text = update.message.text

    if text == "📊 Báo cáo":
        from bot.handlers.progress import show_report
        await show_report(update, context)
    elif text == "🔍 Tìm từ":
        from bot.handlers.search import ask_search
        await ask_search(update, context)
    elif text == "📋 Bộ từ của tôi":
        from bot.handlers.myset import myset_start
        await myset_start(update, context)
    elif text == "📚 Học từ vựng":
        await study_start(update, context)
        return CHOOSE_SOURCE
    elif text in ("🏠 Trang chủ",):
        from bot.handlers.start import start
        await start(update, context)
    elif text == "💝 Ủng hộ":
        from bot.handlers.start import donate
        await donate(update, context)
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("study", study_start),
            MessageHandler(filters.Regex("^📚 Học từ vựng$"), study_start),
        ],
        states={
            CHOOSE_SOURCE: [CallbackQueryHandler(choose_source)],
            CHOOSE_LEVEL: [CallbackQueryHandler(choose_level)],
            CHOOSE_SUBCAT: [CallbackQueryHandler(choose_subcat)],
            CHOOSE_CUSTOM_SET: [CallbackQueryHandler(choose_custom_set)],
            CHOOSE_MODE: [CallbackQueryHandler(choose_mode)],
            STUDYING: [
                CommandHandler("stop", stop),
                MessageHandler(
                    filters.Regex("^(📊 Báo cáo|🔍 Tìm từ|📋 Bộ từ của tôi|📚 Học từ vựng|🏠 Trang chủ|💝 Ủng hộ)$"),
                    cancel_to_menu,
                ),
                CallbackQueryHandler(_hint_callback, pattern=r"^typing_hint$"),
                CallbackQueryHandler(_studying_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _studying_message),
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
            CommandHandler("menu", stop),
            MessageHandler(
                filters.Regex("^(📊 Báo cáo|🔍 Tìm từ|📋 Bộ từ của tôi|📚 Học từ vựng|🏠 Trang chủ|💝 Ủng hộ)$"),
                cancel_to_menu,
            ),
        ],
        per_message=False,
    )
    app.add_handler(conv)
    # Global fallback: fc: callbacks when no active conversation (e.g. after bot restart)
    from telegram.ext import CallbackQueryHandler as CQH
    from bot.handlers.flashcard import handle_fc_global
    app.add_handler(CQH(handle_fc_global, pattern=r"^fc:"))


async def _hint_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from bot.handlers.typing import handle_hint_callback
    return await handle_hint_callback(update, context)


async def _studying_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mode = context.user_data.get("mode")
    if mode == MODE_FLASHCARD:
        from bot.handlers.flashcard import handle_flashcard_callback
        return await handle_flashcard_callback(update, context)
    elif mode == MODE_QUIZ:
        from bot.handlers.quiz import handle_quiz_callback
        return await handle_quiz_callback(update, context)
    return STUDYING


async def _studying_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mode = context.user_data.get("mode")
    if mode == MODE_TYPING:
        from bot.handlers.typing import handle_typing_answer
        return await handle_typing_answer(update, context)
    return STUDYING
