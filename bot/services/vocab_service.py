from bot.db import vocab_db


def get_levels():
    return vocab_db.get_levels()


def get_levels_with_subcat_count():
    return vocab_db.get_levels_with_subcat_count()


def get_subcategories(level_sql_id: int):
    return vocab_db.get_subcategories(level_sql_id)


def get_vocab_list(subcat_id: int | None = None, vocab_ids: list[int] | None = None) -> list[dict]:
    if vocab_ids is not None:
        return vocab_db.get_vocab_by_ids(vocab_ids)
    if subcat_id is not None:
        return vocab_db.get_vocab_by_subcat(subcat_id)
    return []


def get_vocab_detail(vocab_sql_id: int) -> dict | None:
    return vocab_db.get_vocab_detail(vocab_sql_id)


def search(query: str) -> list[dict]:
    return vocab_db.search_vocab(query)
