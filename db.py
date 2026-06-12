from __future__ import annotations

import sqlite3

from models import Birthday, User


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    lookahead_days  INTEGER NOT NULL DEFAULT 7,
    reminder_hour   INTEGER NOT NULL DEFAULT 9,
    last_sent_date  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS birthdays (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    month       INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    day         INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
    year        INTEGER,
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_birthdays_user_id ON birthdays(user_id);
"""

_USER_COLUMNS = "user_id, timezone, lookahead_days, reminder_hour, last_sent_date"


def connect(db_path: str) -> sqlite3.Connection:
    """Opens a SQLite connection at db_path and ensures the schema exists."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def get_or_create_user(conn: sqlite3.Connection, user_id: int) -> User:
    user = get_user(conn, user_id)
    if user is not None:
        return user

    conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    return User(user_id=user_id, timezone="UTC", lookahead_days=7, reminder_hour=9, last_sent_date=None)


def get_user(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute(
        f"SELECT {_USER_COLUMNS} FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return User(*row) if row else None


def get_all_users(conn: sqlite3.Connection) -> list[User]:
    rows = conn.execute(f"SELECT {_USER_COLUMNS} FROM users").fetchall()
    return [User(*row) for row in rows]


def update_timezone(conn: sqlite3.Connection, user_id: int, timezone: str) -> None:
    conn.execute("UPDATE users SET timezone = ? WHERE user_id = ?", (timezone, user_id))
    conn.commit()


def update_lookahead_days(conn: sqlite3.Connection, user_id: int, days: int) -> None:
    conn.execute("UPDATE users SET lookahead_days = ? WHERE user_id = ?", (days, user_id))
    conn.commit()


def update_last_sent_date(conn: sqlite3.Connection, user_id: int, date_str: str) -> None:
    conn.execute("UPDATE users SET last_sent_date = ? WHERE user_id = ?", (date_str, user_id))
    conn.commit()


_BIRTHDAY_COLUMNS = "id, user_id, name, month, day, year, notes"


def add_birthday(
    conn: sqlite3.Connection,
    user_id: int,
    name: str,
    month: int,
    day: int,
    year: int | None,
    notes: str | None,
) -> int:
    cur = conn.execute(
        "INSERT INTO birthdays (user_id, name, month, day, year, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, month, day, year, notes),
    )
    conn.commit()
    return cur.lastrowid


def get_user_birthdays(conn: sqlite3.Connection, user_id: int) -> list[Birthday]:
    rows = conn.execute(
        f"SELECT {_BIRTHDAY_COLUMNS} FROM birthdays WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return [Birthday(*row) for row in rows]


def get_birthday(conn: sqlite3.Connection, birthday_id: int, user_id: int) -> Birthday | None:
    row = conn.execute(
        f"SELECT {_BIRTHDAY_COLUMNS} FROM birthdays WHERE id = ? AND user_id = ?",
        (birthday_id, user_id),
    ).fetchone()
    return Birthday(*row) if row else None


def update_birthday(
    conn: sqlite3.Connection,
    birthday_id: int,
    user_id: int,
    name: str,
    month: int,
    day: int,
    year: int | None,
    notes: str | None,
) -> bool:
    cur = conn.execute(
        "UPDATE birthdays SET name = ?, month = ?, day = ?, year = ?, notes = ? "
        "WHERE id = ? AND user_id = ?",
        (name, month, day, year, notes, birthday_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_birthday(conn: sqlite3.Connection, birthday_id: int, user_id: int) -> bool:
    cur = conn.execute(
        "DELETE FROM birthdays WHERE id = ? AND user_id = ?",
        (birthday_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0
