from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING, ConversationHandler
from bot.services import user_service


def _build_card_text(vocab: dict) -> str:
    lines = [f"🔤 *{vocab['word']}*"]
    if vocab.get("pronunciationIpa"):
        lines.append(f"📢 /{vocab['pronunciationIpa']}/")
    if vocab.get("meaningVi"):
        lines.append(f"\n🇻🇳 {vocab['meaningVi']}")
    if vocab.get("synonyms"):
        lines.append(f"🔗 _{vocab['synonyms']}_")
    return "\n".join(lines)


async def send_flashcard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if session is done."""
    vocab_list: list[dict] = context.user_data["vocab_list"]
    index: int = context.user_data.get("vocab_index", 0)

    if index >= len(vocab_list):
        chat = update.effective_chat
        await context.bot.send_message(
            chat.id,
            "🎉 Bạn đã học hết tất cả từ trong phiên này\\!\nNhấn menu để tiếp tục\\.",
            parse_mode="MarkdownV2",
        )
        context.user_data.clear()
        return True

    vocab = vocab_list[index]
    text = _build_card_text(vocab)
    text += f"\n\n_{index + 1}/{len(vocab_list)}_"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Biết rồi", callback_data="fc:know"),
            InlineKeyboardButton("❌ Chưa biết", callback_data="fc:unknown"),
        ]
    ])

    chat = update.effective_chat
    if vocab.get("imageUrl"):
        await context.bot.send_photo(
            chat.id,
            photo=vocab["imageUrl"],
            caption=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        await context.bot.send_message(
            chat.id, text, parse_mode="Markdown", reply_markup=keyboard
        )
    return False


async def handle_flashcard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("fc:"):
        return STUDYING

    vocab_list: list[dict] = context.user_data["vocab_list"]
    index: int = context.user_data.get("vocab_index", 0)
    vocab = vocab_list[index]
    correct = data == "fc:know"

    user_service.upsert_word_progress(
        telegram_id=query.from_user.id,
        vocab_id=int(vocab["sqlId"]),
        correct=correct,
    )

    context.user_data["vocab_index"] = index + 1
    done = await send_flashcard(update, context)
    return ConversationHandler.END if done else STUDYING
