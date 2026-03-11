import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.config/wad-evoker/library.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS wads (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            filename      TEXT NOT NULL,
            filepath      TEXT NOT NULL UNIQUE,
            author        TEXT,
            description   TEXT,
            year          TEXT,
            game          TEXT,
            map_count     TEXT,
            titlepic_path TEXT,
            added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_played   TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tags (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            wad_id  INTEGER NOT NULL REFERENCES wads(id) ON DELETE CASCADE,
            tag     TEXT NOT NULL,
            UNIQUE(wad_id, tag)
        );
    """)
    # Migration: add titlepic_path to existing installs
    try:
        c.execute("ALTER TABLE wads ADD COLUMN titlepic_path TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.commit()
    conn.close()


# ── WAD CRUD ──────────────────────────────────────────────────────────────────

def add_wad(title, filename, filepath, author=None, description=None,
            year=None, game=None, map_count=None, titlepic_path=None):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO wads (title, filename, filepath, author, description, year, game, map_count, titlepic_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, filename, filepath, author, description, year, game, map_count, titlepic_path)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM wads WHERE filepath = ?", (filepath,)).fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        return None  # already exists
    finally:
        conn.close()


def get_all_wads():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM wads ORDER BY title COLLATE NOCASE").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_last_played(limit=5):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM wads WHERE last_played IS NOT NULL ORDER BY last_played DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_titlepic(wad_id, titlepic_path):
    conn = get_connection()
    conn.execute(
        "UPDATE wads SET titlepic_path = ? WHERE id = ?",
        (titlepic_path, wad_id)
    )
    conn.commit()
    conn.close()


def update_last_played(wad_id):
    conn = get_connection()
    conn.execute(
        "UPDATE wads SET last_played = ? WHERE id = ?",
        (datetime.now().isoformat(), wad_id)
    )
    conn.commit()
    conn.close()


def delete_wad(wad_id):
    conn = get_connection()
    conn.execute("DELETE FROM wads WHERE id = ?", (wad_id,))
    conn.commit()
    conn.close()


def search_wads(query):
    conn = get_connection()
    q = f"%{query}%"
    rows = conn.execute(
        """SELECT DISTINCT w.* FROM wads w
           LEFT JOIN tags t ON t.wad_id = w.id
           WHERE w.title LIKE ? OR w.author LIKE ? OR t.tag LIKE ?
           ORDER BY w.title COLLATE NOCASE""",
        (q, q, q)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── TAGS ──────────────────────────────────────────────────────────────────────

def get_tags(wad_id):
    conn = get_connection()
    rows = conn.execute("SELECT tag FROM tags WHERE wad_id = ? ORDER BY tag", (wad_id,)).fetchall()
    conn.close()
    return [r["tag"] for r in rows]


def add_tag(wad_id, tag):
    tag = tag.strip()
    if not tag:
        return
    conn = get_connection()
    try:
        conn.execute("INSERT INTO tags (wad_id, tag) VALUES (?, ?)", (wad_id, tag))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


def remove_tag(wad_id, tag):
    conn = get_connection()
    conn.execute("DELETE FROM tags WHERE wad_id = ? AND tag = ?", (wad_id, tag))
    conn.commit()
    conn.close()
