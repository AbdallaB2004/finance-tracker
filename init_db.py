"""Initialise the SQLite database.

Run once before starting the app:
    python init_db.py
"""
import os
import sqlite3

DB_PATH = 'finance.db'
SCHEMA_PATH = 'schema.sql'


def init_db():
    if os.path.exists(DB_PATH):
        confirm = input(f"{DB_PATH} already exists. Recreate? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Created {DB_PATH}")


if __name__ == '__main__':
    init_db()
