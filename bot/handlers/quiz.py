from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING
from bot.services import quiz_service, user_service


async def send_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    vocab_list: list[dict] = context.user_data["vocab_list"]
    index: int = context.user_data.get("vocab_index", 0)
    chat = update.effective_chat

    if index >= len(vocab_list):
        await context.bot.send_message(chat.id, "🎉 Bạn đã hoàn thành phiên trắc nghiệm\\!", parse_mode="MarkdownV2")
        context.user_data.clear()
        return

    vocab = vocab_list[index]
    question = quiz_service.make_quiz_question(vocab)
    context.user_data["current_question"] = question

    buttons = [
        [InlineKeyboardButton(f"{i+1}. {choice}", callback_data=f"quiz:{i}")]
        for i, choice in enumerate(question["choices"])
    ]

    caption = f"*{vocab['word']}*"
    if vocab.get("pronunciationIpa"):
        caption += f"\n📢 /{vocab['pronunciationIpa']}/"
    caption += f"\n\n_{index + 1}/{len(vocab_list)}_\n\n🇻🇳 *Nghĩa là gì?*"

    if vocab.get("imageUrl"):
        await context.bot.send_photo(
            chat.id,
            photo=vocab["imageUrl"],
            caption=caption,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        await context.bot.send_message(
            chat.id, caption, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def handle_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("quiz:"):
        return STUDYING

    chosen_index = int(data.split(":")[1])
    question: dict = context.user_data.get("current_question", {})
    vocab: dict = question.get("vocab", {})
    correct = chosen_index == question.get("answer_index")
    correct_meaning = question["choices"][question["answer_index"]]

    if correct:
        result_text = f"✅ *Đúng rồi\\!* {correct_meaning}"
    else:
        chosen_meaning = question["choices"][chosen_index]
        result_text = (
            f"❌ *Sai\\!* Bạn chọn: _{chosen_meaning}_\n"
            f"✅ Đáp án: *{correct_meaning}*"
        )

    await query.edit_message_caption(
        caption=query.message.caption + f"\n\n{result_text}",
        parse_mode="MarkdownV2",
    ) if query.message.caption else await query.edit_message_text(
        text=query.message.text + f"\n\n{result_text}",
        parse_mode="MarkdownV2",
    )

    user_service.upsert_word_progress(
        telegram_id=query.from_user.id,
        vocab_id=vocab["sqlId"],
        correct=correct,
    )

    vocab_list: list[dict] = context.user_data["vocab_list"]
    context.user_data["vocab_index"] = context.user_data.get("vocab_index", 0) + 1

    await send_quiz(update, context)
    return STUDYING
