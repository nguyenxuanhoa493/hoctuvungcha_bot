import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING, ConversationHandler
from bot.services import quiz_service, user_service


def _max_hints(word: str) -> int:
    """Only for words > 5 non-space chars. Base 2, +1 per 3 extra chars."""
    n = len(word.replace(" ", ""))
    if n <= 5:
        return 0
    return 2 + max(0, (n - 6) // 3)


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
