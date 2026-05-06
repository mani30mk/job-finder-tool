"""
Run once to add Gemini scoring columns to existing DB.
Safe to run multiple times (uses IF NOT EXISTS pattern).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "jobs.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("gemini_score",   "REAL DEFAULT 0"),
        ("gemini_reasons", "TEXT DEFAULT '[]'"),
        ("gemini_summary", "TEXT DEFAULT ''"),
    ]

    for col_name, col_def in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")
            print(f"  Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  Column already exists: {col_name}")
            else:
                raise

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
