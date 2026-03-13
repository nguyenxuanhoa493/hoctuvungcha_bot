"""
Export langeek_vocab.db to JSONL files, then import into Convex.

Usage:
    python scripts/import_vocab_to_convex.py [--db path/to/langeek_vocab.db]

This will:
1. Export each table to a .jsonl file in scripts/export/
2. Run `npx convex import` for each table
"""
import sqlite3
import json
import os
import sys
import argparse
import subprocess

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "export")


def export_table(conn: sqlite3.Connection, table: str, transform) -> str:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()

    os.makedirs(EXPORT_DIR, exist_ok=True)
    out_path = os.path.join(EXPORT_DIR, f"{table}.jsonl")

    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            doc = transform(dict(row))
            if doc:
                # Remove None values — Convex treats absent fields as optional
                doc = {k: v for k, v in doc.items() if v is not None}
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"  Exported {len(rows)} rows → {out_path}")
    return out_path


def convex_import(table_name: str, file_path: str, append: bool = False) -> None:
    flag = "--append" if append else "--replace"
    cmd = ["npx", "convex", "import", flag, "--yes", "--table", table_name, file_path]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Error:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✓ Imported into Convex table '{table_name}'")


def main():
    parser = argparse.ArgumentParser(description="Import vocab SQLite data into Convex")
    parser.add_argument("--db", default="langeek_vocab.db", help="Path to SQLite DB")
    parser.add_argument("--append", action="store_true", help="Append instead of replace")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"✗ Database not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    tables = [
        (
            "levels",
            "levels",
            lambda r: {
                "sqlId": r["id"],
                "title": r["title"] or "",
                "originalTitle": r.get("original_title") or None,
                "urlId": r.get("url_id") or "",
            },
        ),
        (
            "subcategories",
            "subcategories",
            lambda r: {
                "sqlId": r["id"],
                "levelSqlId": r["level_id"],
                "title": r["title"] or "",
                "originalTitle": r.get("original_title") or None,
                "urlId": r.get("url_id") or None,
                "position": r.get("position"),
            },
        ),
        (
            "vocabularies",
            "vocabularies",
            lambda r: {
                "sqlId": r["id"],
                "subcategorySqlId": r["subcategory_id"],
                "word": r["word"] or "",
                "pronunciation": r.get("pronunciation") or None,
                "pronunciationIpa": r.get("pronunciation_ipa") or None,
                "audioUrl": r.get("audio_url") or None,
                "meaningVi": r.get("meaning_vi") or None,
                "synonyms": r.get("synonyms") or None,
                "imageUrl": r.get("image_url") or None,
            },
        ),
        (
            "examples",
            "examples",
            lambda r: {
                "sqlId": r["id"],
                "vocabSqlId": r["vocab_id"],
                "exampleEn": r.get("example_en") or None,
                "exampleVi": r.get("example_vi") or None,
                "audioUrl": r.get("audio_url") or None,
            },
        ),
    ]

    print("=== Phase 1: Export SQLite → JSONL ===")
    for sqlite_table, convex_table, transform in tables:
        print(f"\n[{sqlite_table}]")
        export_table(conn, sqlite_table, transform)

    conn.close()

    print("\n=== Phase 2: Import JSONL → Convex ===")
    for sqlite_table, convex_table, _ in tables:
        print(f"\n[{convex_table}]")
        file_path = os.path.join(EXPORT_DIR, f"{sqlite_table}.jsonl")
        convex_import(convex_table, file_path, append=args.append)

    print("\n✅ Migration complete!")
    print("You can now remove the local langeek_vocab.db dependency from the bot.")


if __name__ == "__main__":
    main()
