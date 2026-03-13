from bot.db.convex_client import get_client


def upsert_user(telegram_id: int, username: str | None, first_name: str) -> None:
    get_client().mutation("users:upsertUser", {
        "telegramId": telegram_id,
        "username": username,
        "firstName": first_name,
    })


def get_word_progress(telegram_id: int, vocab_id: int) -> dict | None:
    return get_client().query("progress:getWordProgress", {
        "telegramId": telegram_id,
        "vocabId": vocab_id,
    })


def upsert_word_progress(
    telegram_id: int,
    vocab_id: int,
    correct: bool,
) -> None:
    get_client().mutation("progress:upsertWordProgress", {
        "telegramId": telegram_id,
        "vocabId": vocab_id,
        "correct": correct,
    })


def get_stats(telegram_id: int) -> dict:
    result = get_client().query("progress:getStats", {"telegramId": telegram_id})
    return result or {"new": 0, "learning": 0, "known": 0, "total": 0}


def list_custom_sets(telegram_id: int) -> list[dict]:
    return get_client().query("customSets:listSets", {"telegramId": telegram_id}) or []


def create_custom_set(telegram_id: int, name: str) -> str:
    """Returns the new set _id."""
    return get_client().mutation("customSets:createSet", {
        "telegramId": telegram_id,
        "name": name,
    })


def add_word_to_set(set_id: str, vocab_id: int) -> None:
    get_client().mutation("customSets:addWord", {"setId": set_id, "vocabId": vocab_id})


def remove_word_from_set(set_id: str, vocab_id: int) -> None:
    get_client().mutation("customSets:removeWord", {"setId": set_id, "vocabId": vocab_id})


def delete_custom_set(set_id: str) -> None:
    get_client().mutation("customSets:deleteSet", {"setId": set_id})


def get_custom_set(set_id: str) -> dict | None:
    return get_client().query("customSets:getSet", {"setId": set_id})
