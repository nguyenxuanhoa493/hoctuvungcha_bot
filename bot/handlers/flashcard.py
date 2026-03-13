from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING, ConversationHandler
from bot.services import user_service, vocab_service


def _card_front_text(vocab: dict, index: int, total: int) -> str:
    lines = [f"🔤 <b>{vocab['word']}</b>"]
    ipa = vocab.get("pronunciationIpa") or vocab.get("pronunciation")
    if ipa:
        lines.append(f"📢 <code>/{ipa}/</code>")
    lines.append(f"\n<i>{index + 1}/{total}</i>")
    return "\n".join(lines)


def _card_back_text(vocab: dict, index: int, total: int) -> str:
    lines = [f"🔤 <b>{vocab['word']}</b>"]
    ipa = vocab.get("pronunciationIpa") or vocab.get("pronunciation")
    if ipa:
        lines.append(f"📢 <code>/{ipa}/</code>")
    lines.append(f"🇻🇳 <b>{vocab.get('meaningVi', '')}</b>")
    if vocab.get("synonyms"):
        lines.append(f"🔗 <i>{vocab['synonyms']}</i>")
    lines.append(f"\n<i>{index + 1}/{total}</i>")
    return "\n".join(lines)


def _card_keyboard(face: str, vocab_id: int, has_audio: bool) -> InlineKeyboardMarkup:
    flip_label = "🔄 Xem nghĩa" if face == "front" else "🔄 Xem từ"
    top_row = [InlineKeyboardButton(flip_label, callback_data=f"fc:flip:{vocab_id}:{face}")]
    if has_audio:
        top_row.append(InlineKeyboardButton("🔊 Nghe", callback_data=f"fc:audio:{vocab_id}"))
    return InlineKeyboardMarkup([
        top_row,
        [
            InlineKeyboardButton("✅ Biết rồi", callback_data=f"fc:know:{vocab_id}"),
            InlineKeyboardButton("❌ Chưa biết", callback_data=f"fc:unknown:{vocab_id}"),
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
    vocab_id = int(vocab["sqlId"])
    context.user_data["fc_face"] = "front"
    text = _card_front_text(vocab, index, len(vocab_list))
    keyboard = _card_keyboard("front", vocab_id, bool(vocab.get("audioUrl")))
    chat = update.effective_chat

    # Front side: always text only (no image)
    await context.bot.send_message(chat.id, text, parse_mode="HTML", reply_markup=keyboard)
    return False


async def handle_flashcard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _process_fc_callback(update, context, from_conversation=True)


async def handle_fc_global(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global fallback handler for fc: callbacks when conversation state is lost."""
    await _process_fc_callback(update, context, from_conversation=False)


async def _process_fc_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, from_conversation: bool
) -> int:
    query = update.callback_query
    data = query.data

    if data == "fc:noop":
        await query.answer("Bạn đã chọn rồi ✓")
        return STUDYING

    await query.answer()

    parts = data.split(":")
    action = parts[1]  # flip / audio / know / unknown

    # Parse vocab_id from callback_data (new format: fc:action:vocab_id[:face])
    if len(parts) < 3:
        return STUDYING

    try:
        vocab_id = int(parts[2])
    except ValueError:
        return STUDYING

    # Try to get vocab from user_data first, fall back to DB fetch
    vocab = None
    vocab_list: list[dict] = context.user_data.get("vocab_list", [])
    index: int = context.user_data.get("vocab_index", 0)
    total = len(vocab_list)

    if vocab_list and index < len(vocab_list) and int(vocab_list[index]["sqlId"]) == vocab_id:
        vocab = vocab_list[index]
    else:
        vocab = vocab_service.get_vocab_detail(vocab_id)
        # Reconstruct minimal context if needed
        index = 0
        total = 1

    if not vocab:
        return STUDYING

    if action == "flip":
        current_face = parts[3] if len(parts) > 3 else context.user_data.get("fc_face", "front")
        new_face = "back" if current_face == "front" else "front"
        if from_conversation:
            context.user_data["fc_face"] = new_face

        has_audio = bool(vocab.get("audioUrl"))
        keyboard = _card_keyboard(new_face, vocab_id, has_audio)

        if new_face == "back":
            text = _card_back_text(vocab, index, total)
            # Edit text, then send image separately if available
            try:
                await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                pass
            if vocab.get("imageUrl"):
                try:
                    await context.bot.send_photo(query.message.chat_id, photo=vocab["imageUrl"])
                except Exception:
                    pass
        else:
            text = _card_front_text(vocab, index, total)
            try:
                await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                pass
        return STUDYING

    if action == "audio":
        audio_url = vocab.get("audioUrl")
        if audio_url:
            try:
                await context.bot.send_voice(query.message.chat.id, voice=audio_url)
            except Exception:
                pass
        return STUDYING

    if action in ("know", "unknown"):
        correct = action == "know"
        user_service.upsert_word_progress(
            telegram_id=query.from_user.id,
            vocab_id=vocab_id,
            correct=correct,
        )
        await query.edit_message_reply_markup(reply_markup=_done_keyboard(correct))

        if from_conversation and vocab_list:
            context.user_data["vocab_index"] = index + 1
            done = await send_flashcard(update, context)
            return ConversationHandler.END if done else STUDYING

        return STUDYING

    return STUDYING



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
