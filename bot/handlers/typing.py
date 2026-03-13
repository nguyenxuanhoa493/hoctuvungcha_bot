from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING, ConversationHandler
from bot.services import quiz_service, user_service


def _word_hint(word: str) -> str:
    """Convert word to underscore hint. Multi-word separated by 3 spaces."""
    parts = word.split(" ")
    return "   ".join(" ".join("_" for _ in part) for part in parts)


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

    hint = _word_hint(vocab["word"])
    lines = [f"⌨️ <b>Gõ từ tiếng Anh</b>  <i>{index + 1}/{len(vocab_list)}</i>", ""]
    lines.append(f"🇻🇳 Nghĩa: <b>{vocab.get('meaningVi', '?')}</b>")
    ipa = vocab.get("pronunciationIpa") or vocab.get("pronunciation")
    if ipa:
        lines.append(f"📢 <code>/{ipa}/</code>")
    lines.append(f"\n💡 <code>{hint}</code>")

    text = "\n".join(lines)

    if vocab.get("imageUrl"):
        await context.bot.send_photo(
            chat.id, photo=vocab["imageUrl"], caption=text, parse_mode="HTML",
        )
    else:
        await context.bot.send_message(chat.id, text, parse_mode="HTML")
    return False


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
