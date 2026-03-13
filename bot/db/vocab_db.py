from bot.db.convex_client import get_client


def get_levels() -> list[dict]:
    return get_client().query("vocab:getLevels") or []


def get_subcategories(level_sql_id: int) -> list[dict]:
    return get_client().query("vocab:getSubcategoriesByLevel", {"levelSqlId": level_sql_id}) or []


def get_vocab_by_subcat(subcat_sql_id: int) -> list[dict]:
    return get_client().query("vocab:getVocabBySubcategory", {"subcategorySqlId": subcat_sql_id}) or []


def get_vocab_by_ids(sql_ids: list[int]) -> list[dict]:
    if not sql_ids:
        return []
    return get_client().query("vocab:getVocabBySqlIds", {"sqlIds": sql_ids}) or []


def get_vocab_by_id(sql_id: int) -> dict | None:
    return get_client().query("vocab:getVocabBySqlId", {"sqlId": sql_id})


def get_vocab_detail(sql_id: int) -> dict | None:
    return get_client().query("vocab:getVocabDetail", {"sqlId": sql_id})


def get_examples_by_vocab(vocab_sql_id: int) -> list[dict]:
    return get_client().query("vocab:getExamplesByVocab", {"vocabSqlId": vocab_sql_id}) or []


def search_vocab(query: str, limit: int = 20) -> list[dict]:
    return get_client().query("vocab:searchVocab", {"query": query, "limit": limit}) or []


def get_random_vocab_meanings(exclude_sql_id: int, count: int = 3) -> list[str]:
    return get_client().query(
        "vocab:getRandomVocabMeanings", {"excludeSqlId": exclude_sql_id, "count": count}
    ) or []

