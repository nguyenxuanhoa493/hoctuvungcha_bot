from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING, ConversationHandler
from bot.services import user_service


def _card_front(vocab: dict) -> str:
    lines = [f"🔤 <b>{vocab['word']}</b>"]
    if vocab.get("pronunciationIpa"):
        lines.append(f"📢 /{vocab['pronunciationIpa']}/")
    return "\n".join(lines)


def _card_back(vocab: dict) -> str:
    lines = [f"🔤 <b>{vocab['word']}</b>"]
    lines.append(f"🇻🇳 {vocab.get('meaningVi', '')}")
    if vocab.get("synonyms"):
        lines.append(f"🔗 <i>{vocab['synonyms']}</i>")
    return "\n".join(lines)


def _card_keyboard(face: str, has_audio: bool) -> InlineKeyboardMarkup:
    flip_label = "🔄 Xem nghĩa" if face == "front" else "🔄 Xem từ"
    top_row = [InlineKeyboardButton(flip_label, callback_data="fc:flip")]
    if has_audio:
        top_row.append(InlineKeyboardButton("🔊 Nghe", callback_data="fc:audio"))
    return InlineKeyboardMarkup([
        top_row,
        [
            InlineKeyboardButton("✅ Biết rồi", callback_data="fc:know"),
            InlineKeyboardButton("❌ Chưa biết", callback_data="fc:unknown"),
        ],
    ])


def _done_keyboard(known: bool) -> InlineKeyboardMarkup:
    label = "✅ Biết rồi ✓" if known else "❌ Chưa biết ✓"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="fc:noop")]])


async def send_flashcard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if session is done."""
    vocab_list: list[dict] = context.user_data["vocab_list"]
    index: int = context.user_data.get("vocab_index", 0)

    if index >= len(vocab_list):
        chat = update.effective_chat
        await context.bot.send_message(
            chat.id, "🎉 Bạn đã học hết tất cả từ trong phiên này!\nNhấn menu để tiếp tục.",
        )
        context.user_data.clear()
        return True

    vocab = vocab_list[index]
    context.user_data["fc_face"] = "front"
    text = _card_front(vocab) + f"\n\n<i>{index + 1}/{len(vocab_list)}</i>"
    keyboard = _card_keyboard("front", bool(vocab.get("audioUrl")))
    chat = update.effective_chat

    if vocab.get("imageUrl"):
        await context.bot.send_photo(
            chat.id, photo=vocab["imageUrl"], caption=text,
            parse_mode="HTML", reply_markup=keyboard,
        )
    else:
        await context.bot.send_message(chat.id, text, parse_mode="HTML", reply_markup=keyboard)
    return False


async def handle_flashcard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == "fc:noop":
        await query.answer("Bạn đã chọn rồi ✓")
        return STUDYING

    if not data.startswith("fc:"):
        await query.answer()
        return STUDYING

    await query.answer()

    vocab_list: list[dict] = context.user_data.get("vocab_list", [])
    index: int = context.user_data.get("vocab_index", 0)
    if not vocab_list or index >= len(vocab_list):
        return STUDYING
    vocab = vocab_list[index]

    if data == "fc:flip":
        face = context.user_data.get("fc_face", "front")
        new_face = "back" if face == "front" else "front"
        context.user_data["fc_face"] = new_face
        text = (_card_back(vocab) if new_face == "back" else _card_front(vocab))
        text += f"\n\n<i>{index + 1}/{len(vocab_list)}</i>"
        keyboard = _card_keyboard(new_face, bool(vocab.get("audioUrl")))
        if query.message.caption is not None:
            await query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
        return STUDYING

    if data == "fc:audio":
        audio_url = vocab.get("audioUrl")
        if audio_url:
            await context.bot.send_voice(query.message.chat.id, voice=audio_url)
        return STUDYING

    if data in ("fc:know", "fc:unknown"):
        correct = data == "fc:know"
        user_service.upsert_word_progress(
            telegram_id=query.from_user.id,
            vocab_id=int(vocab["sqlId"]),
            correct=correct,
        )
        await query.edit_message_reply_markup(reply_markup=_done_keyboard(correct))
        context.user_data["vocab_index"] = index + 1
        done = await send_flashcard(update, context)
        return ConversationHandler.END if done else STUDYING

    return STUDYING
