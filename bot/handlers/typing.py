import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING, ConversationHandler
from bot.services import quiz_service, user_service


def _max_hints(word: str, has_image: bool) -> int:
    """All words get hints. Base 2 for <5 chars, +1 per 3 chars.
    If image exists, it counts as one extra hint slot."""
    n = len(word.replace(" ", ""))
    if n < 5:
        base = 2
    else:
        base = 2 + (n - 5) // 3 + 1
    return base + (1 if has_image else 0)


def _word_hint_with_reveals(word: str, revealed: set) -> str:
    """Show revealed chars, replace rest with _. Multi-word separated by 3 spaces."""
    parts = word.split(" ")
    result_parts = []
    idx = 0
    for part in parts:
        chars = []
        for ch in part:
            chars.append(ch if idx in revealed else "_")
            idx += 1
        result_parts.append(" ".join(chars))
    return "   ".join(result_parts)


def _hints_used(revealed: set, image_shown: bool) -> int:
    return len(revealed) + (1 if image_shown else 0)


def _build_hint_keyboard(word: str, has_image: bool, revealed: set, image_shown: bool):
    max_h = _max_hints(word, has_image)
    used = _hints_used(revealed, image_shown)
    if used >= max_h:
        return None
    btn = InlineKeyboardButton(f"💡 Gợi ý ({used}/{max_h})", callback_data="typing_hint")
    return InlineKeyboardMarkup([[btn]])


def _build_prompt_text(vocab: dict, index: int, total: int, revealed: set) -> str:
    word = vocab["word"]
    hint = _word_hint_with_reveals(word, revealed)
    lines = [f"⌨️ <b>Gõ từ tiếng Anh</b>  <i>{index + 1}/{total}</i>", ""]
    lines.append(f"🇻🇳 Nghĩa: <b>{vocab.get('meaningVi', '?')}</b>")
    ipa = vocab.get("pronunciationIpa") or vocab.get("pronunciation")
    if ipa:
        lines.append(f"📢 <code>/{ipa}/</code>")
    lines.append(f"\n✏️ <code>{hint}</code>")
    return "\n".join(lines)


async def send_typing_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if session is done."""
    vocab_list: list[dict] = context.user_data["vocab_list"]
    index: int = context.user_data.get("vocab_index", 0)
    chat = update.effective_chat

    if index >= len(vocab_list):
        await context.bot.send_message(
            chat.id, "🎉 Bạn đã hoàn thành phiên học!\nNhấn menu để tiếp tục.",
        )
        context.user_data.clear()
        return True

    vocab = vocab_list[index]
    has_image = bool(vocab.get("imageUrl"))
    context.user_data["awaiting_answer"] = True
    context.user_data["current_vocab"] = vocab
    context.user_data["hint_revealed"] = set()
    context.user_data["hint_image_shown"] = False
    context.user_data["prompt_has_photo"] = False

    text = _build_prompt_text(vocab, index, len(vocab_list), set())
    keyboard = _build_hint_keyboard(vocab["word"], has_image, set(), False)

    # Always send audio
    audio_url = vocab.get("audioUrl")
    if audio_url:
        try:
            await context.bot.send_voice(chat.id, voice=audio_url)
        except Exception:
            pass

    msg = await context.bot.send_message(
        chat.id, text, parse_mode="HTML", reply_markup=keyboard,
    )
    context.user_data["prompt_message_id"] = msg.message_id
    return False


async def handle_hint_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Use one hint: show image first (if available), then reveal random chars."""
    query = update.callback_query
    await query.answer()

    vocab: dict = context.user_data.get("current_vocab", {})
    if not vocab:
        return STUDYING

    word = vocab["word"]
    has_image = bool(vocab.get("imageUrl"))
    revealed: set = context.user_data.get("hint_revealed", set())
    image_shown: bool = context.user_data.get("hint_image_shown", False)
    max_h = _max_hints(word, has_image)
    used = _hints_used(revealed, image_shown)

    if used >= max_h:
        await query.answer("Đã dùng hết gợi ý!", show_alert=True)
        return STUDYING

    # Show image as first hint if available and not yet shown
    if has_image and not image_shown:
        context.user_data["hint_image_shown"] = True
        image_shown = True
        used += 1
        keyboard = _build_hint_keyboard(word, has_image, revealed, image_shown)
        # Send image and update prompt keyboard
        await context.bot.send_photo(
            query.message.chat_id,
            photo=vocab["imageUrl"],
            caption="🖼 Gợi ý hình ảnh",
        )
        # Update prompt keyboard
        index = context.user_data.get("vocab_index", 0)
        total = len(context.user_data.get("vocab_list", []))
        text = _build_prompt_text(vocab, index, total, revealed)
        try:
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
        except Exception:
            pass
        return STUDYING

    # Reveal a random character
    non_space = word.replace(" ", "")
    unrevealed = [i for i in range(len(non_space)) if i not in revealed]
    if not unrevealed:
        return STUDYING

    revealed.add(random.choice(unrevealed))
    context.user_data["hint_revealed"] = revealed

    index = context.user_data.get("vocab_index", 0)
    total = len(context.user_data.get("vocab_list", []))
    text = _build_prompt_text(vocab, index, total, revealed)
    keyboard = _build_hint_keyboard(word, has_image, revealed, image_shown)

    try:
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass
    return STUDYING


async def handle_typing_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not context.user_data.get("awaiting_answer"):
        return STUDYING

    vocab: dict = context.user_data.get("current_vocab", {})
    if not vocab:
        return STUDYING

    user_input = update.message.text
    correct = quiz_service.check_typed_answer(user_input, vocab)

    if correct:
        await update.message.reply_text(
            f"✅ <b>Chính xác!</b> Từ cần tìm là <b>{vocab['word']}</b>.", parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"❌ <b>Sai rồi!</b> Bạn gõ: <code>{user_input}</code>\n✅ Đáp án: <b>{vocab['word']}</b>",
            parse_mode="HTML",
        )

    user_service.upsert_word_progress(
        telegram_id=update.effective_user.id,
        vocab_id=int(vocab["sqlId"]),
        correct=correct,
    )

    context.user_data["awaiting_answer"] = False
    context.user_data["vocab_index"] = context.user_data.get("vocab_index", 0) + 1
    done = await send_typing_prompt(update, context)
    return ConversationHandler.END if done else STUDYING



def _word_hint_with_reveals(word: str, revealed: set) -> str:
    """Show revealed chars, replace rest with _. Multi-word separated by 3 spaces."""
    parts = word.split(" ")
    result_parts = []
    idx = 0
    for part in parts:
        chars = []
        for ch in part:
            chars.append(ch if idx in revealed else "_")
            idx += 1
        result_parts.append(" ".join(chars))
    return "   ".join(result_parts)


def _build_hint_keyboard(word: str, revealed: set):
    max_h = _max_hints(word)
    used = len(revealed)
    if max_h == 0 or used >= max_h:
        return None
    btn = InlineKeyboardButton(f"💡 Gợi ý ({used}/{max_h})", callback_data="typing_hint")
    return InlineKeyboardMarkup([[btn]])


def _build_prompt_text(vocab: dict, index: int, total: int, revealed: set) -> str:
    word = vocab["word"]
    hint = _word_hint_with_reveals(word, revealed)
    lines = [f"⌨️ <b>Gõ từ tiếng Anh</b>  <i>{index + 1}/{total}</i>", ""]
    lines.append(f"🇻🇳 Nghĩa: <b>{vocab.get('meaningVi', '?')}</b>")
    ipa = vocab.get("pronunciationIpa") or vocab.get("pronunciation")
    if ipa:
        lines.append(f"📢 <code>/{ipa}/</code>")
    lines.append(f"\n✏️ <code>{hint}</code>")
    return "\n".join(lines)


async def send_typing_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if session is done."""
    vocab_list: list[dict] = context.user_data["vocab_list"]
    index: int = context.user_data.get("vocab_index", 0)
    chat = update.effective_chat

    if index >= len(vocab_list):
        await context.bot.send_message(
            chat.id, "🎉 Bạn đã hoàn thành phiên học!\nNhấn menu để tiếp tục.",
        )
        context.user_data.clear()
        return True

    vocab = vocab_list[index]
    context.user_data["awaiting_answer"] = True
    context.user_data["current_vocab"] = vocab
    context.user_data["hint_revealed"] = set()

    text = _build_prompt_text(vocab, index, len(vocab_list), set())
    keyboard = _build_hint_keyboard(vocab["word"], set())

    if vocab.get("imageUrl"):
        msg = await context.bot.send_photo(
            chat.id, photo=vocab["imageUrl"], caption=text, parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        msg = await context.bot.send_message(
            chat.id, text, parse_mode="HTML", reply_markup=keyboard,
        )
    context.user_data["prompt_message_id"] = msg.message_id
    context.user_data["prompt_has_photo"] = bool(vocab.get("imageUrl"))
    return False


async def handle_hint_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reveal one random character as a hint."""
    query = update.callback_query
    await query.answer()

    vocab: dict = context.user_data.get("current_vocab", {})
    if not vocab:
        return STUDYING

    word = vocab["word"]
    revealed: set = context.user_data.get("hint_revealed", set())
    max_h = _max_hints(word)

    if len(revealed) >= max_h:
        await query.answer("Đã dùng hết gợi ý!", show_alert=True)
        return STUDYING

    # All non-space char indices (indexed on word-without-spaces)
    non_space = word.replace(" ", "")
    unrevealed = [i for i in range(len(non_space)) if i not in revealed]
    if not unrevealed:
        return STUDYING

    revealed.add(random.choice(unrevealed))
    context.user_data["hint_revealed"] = revealed

    index = context.user_data.get("vocab_index", 0)
    total = len(context.user_data.get("vocab_list", []))
    text = _build_prompt_text(vocab, index, total, revealed)
    keyboard = _build_hint_keyboard(word, revealed)

    if context.user_data.get("prompt_has_photo"):
        await query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    return STUDYING


async def handle_typing_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not context.user_data.get("awaiting_answer"):
        return STUDYING

    vocab: dict = context.user_data.get("current_vocab", {})
    if not vocab:
        return STUDYING

    user_input = update.message.text
    correct = quiz_service.check_typed_answer(user_input, vocab)

    if correct:
        await update.message.reply_text(
            f"✅ <b>Chính xác!</b> Từ cần tìm là <b>{vocab['word']}</b>.", parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"❌ <b>Sai rồi!</b> Bạn gõ: <code>{user_input}</code>\n✅ Đáp án: <b>{vocab['word']}</b>",
            parse_mode="HTML",
        )

    user_service.upsert_word_progress(
        telegram_id=update.effective_user.id,
        vocab_id=int(vocab["sqlId"]),
        correct=correct,
    )

    context.user_data["awaiting_answer"] = False
    context.user_data["vocab_index"] = context.user_data.get("vocab_index", 0) + 1
    done = await send_typing_prompt(update, context)
    return ConversationHandler.END if done else STUDYING
