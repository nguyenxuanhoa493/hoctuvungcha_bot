import random
from bot.db import vocab_db


def make_quiz_question(vocab: dict) -> dict:
    """
    Returns a dict with:
      - vocab: the target vocab dict
      - choices: list of 4 meaning_vi strings (shuffled)
      - answer_index: index of correct answer in choices
    """
    correct = vocab["meaning_vi"]
    distractors = vocab_db.get_random_vocab_meanings(exclude_sql_id=vocab["sqlId"], count=3)

    # Pad with placeholders if not enough distractors
    while len(distractors) < 3:
        distractors.append("—")

    choices = distractors[:3] + [correct]
    random.shuffle(choices)
    answer_index = choices.index(correct)

    return {
        "vocab": vocab,
        "choices": choices,
        "answer_index": answer_index,
    }


def check_typed_answer(user_input: str, vocab: dict) -> bool:
    """Case-insensitive, strip whitespace comparison."""
    target = vocab["word"].strip().lower()
    answer = user_input.strip().lower()
    return answer == target
