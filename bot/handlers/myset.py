"""Manage custom word sets."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters,
)
from bot.services import user_service, vocab_service

(
    MYSET_MENU,
    MYSET_AWAITING_NAME,
    MYSET_SEARCH,
    MYSET_MANAGE,
) = range(10, 14)


def _sets_keyboard(sets: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"📋 {s['name']} ({len(s.get('vocabIds', []))} từ)", callback_data=f"ms_open:{s['_id']}")]
        for s in sets
    ]
    buttons.append([InlineKeyboardButton("➕ Tạo bộ mới", callback_data="ms_create")])
    buttons.append([InlineKeyboardButton("❌ Đóng", callback_data="ms_close")])
    return InlineKeyboardMarkup(buttons)


async def myset_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    sets = user_service.list_custom_sets(user_id)
    msg = update.message or update.callback_query.message

    if not sets:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tạo bộ mới", callback_data="ms_create")],
            [InlineKeyboardButton("❌ Đóng", callback_data="ms_close")],
        ])
        await msg.reply_text("📋 Bạn chưa có bộ từ nào.", reply_markup=keyboard)
    else:
        await msg.reply_text(
            f"📋 *Bộ từ của bạn* ({len(sets)} bộ):",
            parse_mode="Markdown",
            reply_markup=_sets_keyboard(sets),
        )
    return MYSET_MENU


async def myset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "ms_close":
        await query.edit_message_text("✅ Đã đóng.")
        return ConversationHandler.END

    if data == "ms_create":
        await query.edit_message_text("✏️ Nhập tên cho bộ từ mới:")
        return MYSET_AWAITING_NAME

    if data.startswith("ms_open:"):
        set_id = data.split(":", 1)[1]
        custom_set = user_service.get_custom_set(set_id)
        if not custom_set:
            await query.edit_message_text("⚠️ Không tìm thấy bộ từ.")
            return ConversationHandler.END
        context.user_data["current_set_id"] = set_id
        vocab_ids = custom_set.get("vocabIds", [])
        buttons = [
            [InlineKeyboardButton("🔍 Thêm từ", callback_data="ms_add_word")],
            [InlineKeyboardButton("🗑 Xóa bộ này", callback_data=f"ms_delete:{set_id}")],
            [InlineKeyboardButton("🔙 Quay lại", callback_data="ms_back")],
        ]
        await query.edit_message_text(
            f"📋 *{custom_set['name']}* — {len(vocab_ids)} từ",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return MYSET_MANAGE

    if data == "ms_back":
        sets = user_service.list_custom_sets(user_id)
        await query.edit_message_text(
            f"📋 *Bộ từ của bạn* ({len(sets)} bộ):",
            parse_mode="Markdown",
            reply_markup=_sets_keyboard(sets),
        )
        return MYSET_MENU

    return MYSET_MENU


async def myset_manage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "ms_add_word":
        await query.edit_message_text("🔍 Nhập từ để tìm kiếm và thêm vào bộ:")
        return MYSET_SEARCH

    if data.startswith("ms_delete:"):
        set_id = data.split(":", 1)[1]
        user_service.delete_custom_set(set_id)
        sets = user_service.list_custom_sets(user_id)
        await query.edit_message_text(
            "🗑 Đã xóa bộ từ.\n\n📋 *Bộ từ của bạn:*",
            parse_mode="Markdown",
            reply_markup=_sets_keyboard(sets) if sets else InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Tạo bộ mới", callback_data="ms_create")],
                [InlineKeyboardButton("❌ Đóng", callback_data="ms_close")],
            ]),
        )
        return MYSET_MENU

    if data.startswith("ms_add_confirm:"):
        parts = data.split(":")
        set_id = context.user_data.get("current_set_id")
        vocab_id = int(parts[1])
        user_service.add_word_to_set(set_id, vocab_id)
        await query.edit_message_text(f"✅ Đã thêm từ vào bộ\\!", parse_mode="MarkdownV2")
        return MYSET_MANAGE

    if data == "ms_back":
        sets = user_service.list_custom_sets(user_id)
        await query.edit_message_text(
            f"📋 *Bộ từ của bạn* ({len(sets)} bộ):",
            parse_mode="Markdown",
            reply_markup=_sets_keyboard(sets),
        )
        return MYSET_MENU

    return MYSET_MANAGE


async def myset_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("⚠️ Tên không được để trống, thử lại:")
        return MYSET_AWAITING_NAME
    user_id = update.effective_user.id
    user_service.create_custom_set(user_id, name)
    await update.message.reply_text(f"✅ Đã tạo bộ từ *{name}*\\!", parse_mode="MarkdownV2")
    return await myset_start(update, context)


async def myset_search_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query_text = update.message.text.strip()
    results = vocab_service.search(query_text)
    if not results:
        await update.message.reply_text("❌ Không tìm thấy từ nào. Thử lại:")
        return MYSET_SEARCH

    buttons = [
        [InlineKeyboardButton(
            f"{v['word']} — {v.get('meaningVi', '')}",
            callback_data=f"ms_add_confirm:{v['sqlId']}"
        )]
        for v in results[:8]
    ]
    buttons.append([InlineKeyboardButton("🔙 Quay lại", callback_data="ms_back")])
    await update.message.reply_text(
        f"🔍 Kết quả cho *{query_text}*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return MYSET_MANAGE


async def myset_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Đã huỷ.")
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("myset", myset_start),
            MessageHandler(filters.Regex("^📋 Bộ từ của tôi$"), myset_start),
        ],
        states={
            MYSET_MENU: [CallbackQueryHandler(myset_callback)],
            MYSET_AWAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, myset_receive_name)
            ],
            MYSET_MANAGE: [CallbackQueryHandler(myset_manage_callback)],
            MYSET_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, myset_search_word),
                CallbackQueryHandler(myset_manage_callback),
            ],
        },
        fallbacks=[CommandHandler("cancel", myset_cancel)],
        per_message=False,
    )
    app.add_handler(conv)
