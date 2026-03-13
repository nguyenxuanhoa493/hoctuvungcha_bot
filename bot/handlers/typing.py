import random
from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING
from bot.services import quiz_service, user_service

HINTS = ["meaning_vi", "pronunciation_ipa", "image_url"]


async def send_typing_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    vocab_list: list[dict] = context.user_data["vocab_list"]
    index: int = context.user_data.get("vocab_index", 0)
    chat = update.effective_chat

    if index >= len(vocab_list):
        await context.bot.send_message(chat.id, "🎉 Bạn đã hoàn thành phiên học\\!", parse_mode="MarkdownV2")
        context.user_data.clear()
        return

    vocab = vocab_list[index]
    hint_type = random.choice(HINTS)
    context.user_data["awaiting_answer"] = True
    context.user_data["current_vocab"] = vocab

    prompt_lines = [f"⌨️ *Gõ từ tiếng Anh* _{index + 1}/{len(vocab_list)}_\n"]

    if hint_type == "meaning_vi" and vocab.get("meaningVi"):
        prompt_lines.append(f"🇻🇳 Nghĩa: *{vocab['meaningVi']}*")
    elif hint_type == "pronunciation_ipa" and vocab.get("pronunciationIpa"):
        prompt_lines.append(f"📢 Phiên âm: `/{vocab['pronunciationIpa']}/`")
    else:
        # Fallback to meaning if no image or ipa
        prompt_lines.append(f"🇻🇳 Nghĩa: *{vocab.get('meaningVi', '?')}*")

    if vocab.get("synonyms"):
        prompt_lines.append(f"🔗 Từ đồng nghĩa: _{vocab['synonyms']}_")

    text = "\n".join(prompt_lines)

    if hint_type == "image_url" and vocab.get("imageUrl"):
        await context.bot.send_photo(
            chat.id,
            photo=vocab["imageUrl"],
            caption=text,
            parse_mode="Markdown",
        )
    else:
        await context.bot.send_message(chat.id, text, parse_mode="Markdown")


async def handle_typing_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not context.user_data.get("awaiting_answer"):
        return STUDYING

    vocab: dict = context.user_data.get("current_vocab", {})
    if not vocab:
        return STUDYING

    user_input = update.message.text
    correct = quiz_service.check_typed_answer(user_input, vocab)

    if correct:
        await update.message.reply_text(f"✅ *Chính xác\\!* Từ cần tìm là *{vocab['word']}*\\.", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(
            f"❌ *Sai rồi\\!* Bạn gõ: `{user_input}`\n✅ Đáp án: *{vocab['word']}*",
            parse_mode="MarkdownV2",
        )

    user_service.upsert_word_progress(
        telegram_id=update.effective_user.id,
        vocab_id=int(vocab["sqlId"]),
        correct=correct,
    )

    context.user_data["awaiting_answer"] = False
    context.user_data["vocab_index"] = context.user_data.get("vocab_index", 0) + 1
    await send_typing_prompt(update, context)
    return STUDYING
