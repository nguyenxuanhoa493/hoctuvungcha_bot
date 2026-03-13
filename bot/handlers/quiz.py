from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.handlers.study import STUDYING
from bot.services import quiz_service, user_service


async def send_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if session is done."""
    vocab_list: list[dict] = context.user_data["vocab_list"]
    index: int = context.user_data.get("vocab_index", 0)
    chat = update.effective_chat

    if index >= len(vocab_list):
        await context.bot.send_message(
            chat.id, "🎉 Bạn đã hoàn thành phiên trắc nghiệm!\nNhấn menu để tiếp tục.",
        )
        context.user_data.clear()
        return True

    vocab = vocab_list[index]
    question = quiz_service.make_quiz_question(vocab)
    if not question:
        context.user_data["vocab_index"] = index + 1
        return await send_quiz(update, context)

    context.user_data["current_question"] = question

    buttons = [
        [InlineKeyboardButton(f"{i+1}. {choice}", callback_data=f"quiz:{i}")]
        for i, choice in enumerate(question["choices"])
    ]

    text = f"<b>{vocab['word']}</b>"
    if vocab.get("pronunciationIpa"):
        text += f"\n📢 /{vocab['pronunciationIpa']}/"
    text += f"\n\n<i>{index + 1}/{len(vocab_list)}</i>\n\n🇻🇳 <b>Nghĩa là gì?</b>"

    if vocab.get("imageUrl"):
        await context.bot.send_photo(
            chat.id, photo=vocab["imageUrl"], caption=text,
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        await context.bot.send_message(
            chat.id, text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    return False


async def handle_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from bot.handlers.study import ConversationHandler
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
        result_text = f"\n\n✅ <b>Đúng!</b> {correct_meaning}"
    else:
        chosen_meaning = question["choices"][chosen_index]
        result_text = (
            f"\n\n❌ <b>Sai!</b> Bạn chọn: <i>{chosen_meaning}</i>\n"
            f"✅ Đáp án: <b>{correct_meaning}</b>"
        )

    try:
        if query.message.caption is not None:
            await query.edit_message_caption(
                caption=query.message.caption + result_text,
                parse_mode="HTML",
                reply_markup=None,
            )
        else:
            await query.edit_message_text(
                text=query.message.text + result_text,
                parse_mode="HTML",
                reply_markup=None,
            )
    except Exception:
        await context.bot.send_message(query.message.chat.id, result_text.strip(), parse_mode="HTML")

    user_service.upsert_word_progress(
        telegram_id=query.from_user.id,
        vocab_id=int(vocab["sqlId"]),
        correct=correct,
    )

    context.user_data["vocab_index"] = context.user_data.get("vocab_index", 0) + 1
    done = await send_quiz(update, context)
    return ConversationHandler.END if done else STUDYING
