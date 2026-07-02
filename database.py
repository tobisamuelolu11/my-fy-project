"""
database.py  –  SQLite setup for Academia
Tables: articles, users, search_history
Users identified by email; display name derived from email prefix.
"""

import sqlite3
import pandas as pd
import os
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'scholorfind.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT NOT NULL,
            authors  TEXT,
            journal  TEXT,
            year     INTEGER,
            keywords TEXT,
            abstract TEXT,
            content  TEXT,
            url      TEXT
        )
    """)

    # Migrate older databases that don't have the url column yet
    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(articles)").fetchall()]
    if 'url' not in existing_cols:
        cursor.execute("ALTER TABLE articles ADD COLUMN url TEXT")
        print("✔ Migrated: added 'url' column to articles table.")

    # email replaces username; display_name is editable (defaults to email prefix)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE NOT NULL,
            display_name  TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            provider      TEXT DEFAULT 'email',
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query         TEXT NOT NULL,
            results_count INTEGER,
            searched_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✔ Tables created.")


def seed_articles():
    conn   = get_connection()
    cursor = conn.cursor()
    count  = cursor.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    if count > 0:
        print(f"✔ Articles already seeded ({count} rows). Skipping.")
        conn.close()
        return

    csv_path = os.path.join(BASE_DIR, 'articles.csv')
    df = pd.read_csv(csv_path)
    df['content'] = (df['title'].fillna('') + ' ' +
                     df['keywords'].fillna('') + ' ' +
                     df['abstract'].fillna(''))
    # No real publisher link for these sample rows — fall back to a Google Scholar search
    import urllib.parse
    df['url'] = df['title'].fillna('').apply(
        lambda t: f"https://scholar.google.com/scholar?q={urllib.parse.quote(t)}"
    )
    rows = df[['title','authors','journal','year','keywords','abstract','content','url']].values.tolist()
    cursor.executemany(
        "INSERT INTO articles (title,authors,journal,year,keywords,abstract,content,url) VALUES (?,?,?,?,?,?,?,?)",
        rows
    )
    conn.commit()
    conn.close()
    print(f"✔ Seeded {len(rows)} articles.")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def email_to_display(email: str) -> str:
    """Convert email to a friendly display name: john.doe@... → John Doe"""
    prefix = email.split('@')[0]
    return ' '.join(p.capitalize() for p in prefix.replace('.', ' ').replace('_', ' ').split())


def create_user(email: str, password: str):
    email = email.strip().lower()
    display_name = email_to_display(email)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, display_name, password_hash) VALUES (?, ?, ?)",
            (email, display_name, hash_password(password))
        )
        conn.commit()
        return True, {'id': cursor.lastrowid, 'email': email, 'display_name': display_name}
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        conn.close()


def verify_user(email: str, password: str):
    email = email.strip().lower()
    conn  = get_connection()
    row   = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password_hash = ?",
        (email, hash_password(password))
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_articles():
    conn  = get_connection()
    rows  = conn.execute("SELECT * FROM articles").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_search(user_id: int, query: str, results_count: int):
    conn = get_connection()
    conn.execute(
        "INSERT INTO search_history (user_id, query, results_count) VALUES (?, ?, ?)",
        (user_id, query, results_count)
    )
    conn.commit()
    conn.close()


def get_user_history(user_id: int, limit: int = 20):
    conn = get_connection()
    rows = conn.execute(
        """SELECT query, results_count, searched_at FROM search_history
           WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?""",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def init_db():
    create_tables()
    seed_articles()


if __name__ == '__main__':
    init_db()
    print(f"DB ready: {DB_PATH}")
