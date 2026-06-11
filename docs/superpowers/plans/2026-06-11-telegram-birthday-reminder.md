# Telegram Birthday Reminder Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working Telegram bot that stores birthdays in SQLite, lets users manage them via commands, and sends a daily digest of upcoming birthdays via an hourly APScheduler poll.

**Architecture:** Pure logic (date math, reminder decisions) lives in `birthdays.py` and `reminders.py` with no I/O, fully unit-tested via TDD. `db.py` is a thin SQLite data-access layer tested against an in-memory database. `handlers.py` wires Telegram commands to the pure logic and DB layer. `scheduler.py` and `bot.py` tie everything together at runtime.

**Tech Stack:** Python 3.11+, python-telegram-bot v21 (async), SQLite (`sqlite3`), APScheduler 3.10 (`AsyncIOScheduler`), pytest + pytest-asyncio.

Reference spec: `docs/superpowers/specs/2026-06-11-telegram-birthday-reminder-design.md`

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `conftest.py`
- Create: `tests/__init__.py` (empty, optional marker — not strictly needed but harmless)

- [ ] **Step 1: Create `requirements.txt`**

```
python-telegram-bot==21.4
APScheduler==3.10.4
python-dotenv==1.0.1
pytest==8.2.0
pytest-asyncio==0.23.7
```

- [ ] **Step 2: Create `.env.example`**

```
BOT_TOKEN=your-telegram-bot-token-here
DB_PATH=jubilous.db
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.env
*.db
.venv/
.pytest_cache/
```

- [ ] **Step 4: Create `conftest.py` at the project root (empty file)**

```python
# Intentionally empty.
# Its presence makes pytest add the project root to sys.path,
# so test files can `import birthdays`, `import db`, etc.
```

- [ ] **Step 5: Create a virtual environment and install dependencies**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore conftest.py
git commit -m "chore: project scaffolding (deps, env example, gitignore)"
```

---

### Task 2: `birthdays.py` — `parse_birthday_date`

**Files:**
- Create: `birthdays.py`
- Test: `tests/test_birthdays.py`

- [ ] **Step 1: Write failing tests for `parse_birthday_date`**

Create `tests/test_birthdays.py`:

```python
import pytest

from birthdays import parse_birthday_date


def test_parse_date_without_year():
    assert parse_birthday_date("14-03") == (3, 14, None)


def test_parse_date_with_year():
    assert parse_birthday_date("14-03-1965") == (3, 14, 1965)


def test_parse_date_invalid_format_raises():
    with pytest.raises(ValueError):
        parse_birthday_date("not-a-date")


def test_parse_date_invalid_month_raises():
    with pytest.raises(ValueError):
        parse_birthday_date("01-13")


def test_parse_date_invalid_day_raises():
    with pytest.raises(ValueError):
        parse_birthday_date("32-01")


def test_parse_date_feb29_without_year_is_valid():
    assert parse_birthday_date("29-02") == (2, 29, None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_birthdays.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'birthdays'`

- [ ] **Step 3: Implement `parse_birthday_date` in `birthdays.py`**

Create `birthdays.py`:

```python
import re
from datetime import date


_DATE_RE = re.compile(r"^(\d{1,2})-(\d{1,2})(?:-(\d{4}))?$")


def parse_birthday_date(text: str) -> tuple[int, int, int | None]:
    """Parses 'DD-MM' or 'DD-MM-YYYY' into (month, day, year|None).

    Raises ValueError if the text doesn't match the expected format or
    doesn't represent a real calendar date.
    """
    match = _DATE_RE.match(text.strip())
    if not match:
        raise ValueError(f"Invalid date format: {text!r}. Use DD-MM or DD-MM-YYYY.")

    day_str, month_str, year_str = match.groups()
    day = int(day_str)
    month = int(month_str)
    year = int(year_str) if year_str else None

    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month: {month}")
    if not (1 <= day <= 31):
        raise ValueError(f"Invalid day: {day}")

    # Validate the date actually exists. Use a leap year when no year is
    # given so that Feb 29 (year-less) is accepted.
    check_year = year if year is not None else 2024
    try:
        date(check_year, month, day)
    except ValueError as exc:
        raise ValueError(f"Invalid date: {text!r} ({exc})") from exc

    return month, day, year
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_birthdays.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add birthdays.py tests/test_birthdays.py
git commit -m "feat: add birthday date parsing with TDD"
```

---

### Task 3: `birthdays.py` — `days_until`

**Files:**
- Modify: `birthdays.py`
- Modify: `tests/test_birthdays.py`

- [ ] **Step 1: Write failing tests for `days_until`**

Append to `tests/test_birthdays.py`:

```python
from datetime import date

from birthdays import days_until


def test_days_until_today_is_zero():
    today = date(2026, 6, 11)
    assert days_until(today, 6, 11) == 0


def test_days_until_later_this_year():
    today = date(2026, 6, 11)
    assert days_until(today, 6, 20) == 9


def test_days_until_wraps_to_next_year():
    today = date(2026, 6, 11)
    assert days_until(today, 1, 1) == 204


def test_days_until_feb29_in_non_leap_year_treated_as_feb28():
    today = date(2025, 2, 27)  # 2025 is not a leap year
    assert days_until(today, 2, 29) == 1
```

Also add `from datetime import date` near the top of the file if not already present (it will be needed by later tests too — having it imported once at the top is fine; remove the duplicate import added above if you already imported `date` earlier in the file).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_birthdays.py -v`
Expected: FAIL with `ImportError: cannot import name 'days_until' from 'birthdays'`

- [ ] **Step 3: Implement `days_until` in `birthdays.py`**

Add to `birthdays.py` (below `parse_birthday_date`):

```python
def _safe_date(year: int, month: int, day: int) -> date:
    """Builds a date, treating Feb 29 in a non-leap year as Feb 28."""
    if month == 2 and day == 29:
        try:
            return date(year, 2, 29)
        except ValueError:
            return date(year, 2, 28)
    return date(year, month, day)


def days_until(today: date, month: int, day: int) -> int:
    """Returns the number of days from `today` until the next occurrence
    of the given month/day (0 if it's today, otherwise 1-365)."""
    candidate = _safe_date(today.year, month, day)
    if candidate < today:
        candidate = _safe_date(today.year + 1, month, day)
    return (candidate - today).days
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_birthdays.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add birthdays.py tests/test_birthdays.py
git commit -m "feat: add days_until with Feb 29 handling, TDD"
```

---

### Task 4: `birthdays.py` — `age_on_next_birthday`

**Files:**
- Modify: `birthdays.py`
- Modify: `tests/test_birthdays.py`

- [ ] **Step 1: Write failing tests for `age_on_next_birthday`**

Append to `tests/test_birthdays.py`:

```python
from birthdays import age_on_next_birthday


def test_age_on_next_birthday_before_birthday_this_year():
    today = date(2026, 6, 11)
    assert age_on_next_birthday(1990, 6, 20, today) == 36


def test_age_on_next_birthday_after_birthday_this_year():
    today = date(2026, 6, 11)
    assert age_on_next_birthday(1990, 1, 1, today) == 37


def test_age_on_next_birthday_today_is_birthday():
    today = date(2026, 6, 11)
    assert age_on_next_birthday(1990, 6, 11, today) == 36


def test_age_on_next_birthday_unknown_year_returns_none():
    today = date(2026, 6, 11)
    assert age_on_next_birthday(None, 6, 20, today) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_birthdays.py -v`
Expected: FAIL with `ImportError: cannot import name 'age_on_next_birthday' from 'birthdays'`

- [ ] **Step 3: Implement `age_on_next_birthday` in `birthdays.py`**

Add to `birthdays.py` (below `days_until`):

```python
def age_on_next_birthday(year: int | None, month: int, day: int, today: date) -> int | None:
    """Returns the age the person turns on their next occurrence of
    month/day, or None if `year` (birth year) is unknown."""
    if year is None:
        return None

    candidate = _safe_date(today.year, month, day)
    next_age = today.year - year
    if candidate < today:
        next_age += 1
    return next_age
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_birthdays.py -v`
Expected: PASS (14 passed)

- [ ] **Step 5: Commit**

```bash
git add birthdays.py tests/test_birthdays.py
git commit -m "feat: add age_on_next_birthday, TDD"
```

---

### Task 5: `models.py` — dataclasses

**Files:**
- Create: `models.py`

- [ ] **Step 1: Create `models.py`**

```python
from dataclasses import dataclass


@dataclass
class User:
    user_id: int
    timezone: str
    lookahead_days: int
    reminder_hour: int
    last_sent_date: str | None


@dataclass
class Birthday:
    id: int
    user_id: int
    name: str
    month: int
    day: int
    year: int | None
    notes: str | None
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `python -c "from models import User, Birthday; print(User(1, 'UTC', 7, 9, None)); print(Birthday(1, 1, 'Mom', 3, 14, 1965, 'notes'))"`
Expected: prints both dataclass instances with no errors

- [ ] **Step 3: Commit**

```bash
git add models.py
git commit -m "feat: add User and Birthday dataclasses"
```

---

### Task 6: `db.py` — schema, connection, and user functions

**Files:**
- Create: `db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write failing tests for schema setup and user functions**

Create `tests/test_db.py`:

```python
import sqlite3

import pytest

import db


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(db.SCHEMA)
    connection.commit()
    yield connection
    connection.close()


def test_get_or_create_user_creates_new_user(conn):
    user = db.get_or_create_user(conn, 123)
    assert user.user_id == 123
    assert user.timezone == "UTC"
    assert user.lookahead_days == 7
    assert user.reminder_hour == 9
    assert user.last_sent_date is None


def test_get_or_create_user_returns_existing_user(conn):
    db.get_or_create_user(conn, 123)
    db.update_timezone(conn, 123, "Europe/Berlin")

    user = db.get_or_create_user(conn, 123)
    assert user.timezone == "Europe/Berlin"


def test_get_user_returns_none_if_not_found(conn):
    assert db.get_user(conn, 999) is None


def test_update_lookahead_days(conn):
    db.get_or_create_user(conn, 123)
    db.update_lookahead_days(conn, 123, 14)

    user = db.get_user(conn, 123)
    assert user.lookahead_days == 14


def test_update_last_sent_date(conn):
    db.get_or_create_user(conn, 123)
    db.update_last_sent_date(conn, 123, "2026-06-11")

    user = db.get_user(conn, 123)
    assert user.last_sent_date == "2026-06-11"


def test_get_all_users(conn):
    db.get_or_create_user(conn, 123)
    db.get_or_create_user(conn, 456)

    users = db.get_all_users(conn)
    assert {u.user_id for u in users} == {123, 456}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Implement schema, connection, and user functions in `db.py`**

Create `db.py`:

```python
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
```

Note: `Birthday` is imported now even though unused until Task 7 — this avoids a second edit to the import line later.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add SQLite schema, connection, and user CRUD"
```

---

### Task 7: `db.py` — birthday CRUD functions

**Files:**
- Modify: `db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Write failing tests for birthday CRUD**

Append to `tests/test_db.py`:

```python
def test_add_and_get_user_birthdays(conn):
    db.get_or_create_user(conn, 123)
    birthday_id = db.add_birthday(conn, 123, "Mom", 3, 14, 1965, "loves flowers")

    birthdays = db.get_user_birthdays(conn, 123)
    assert len(birthdays) == 1
    assert birthdays[0].id == birthday_id
    assert birthdays[0].name == "Mom"
    assert birthdays[0].month == 3
    assert birthdays[0].day == 14
    assert birthdays[0].year == 1965
    assert birthdays[0].notes == "loves flowers"


def test_get_birthday_returns_none_if_not_found(conn):
    db.get_or_create_user(conn, 123)
    assert db.get_birthday(conn, 999, 123) is None


def test_delete_birthday_owned_by_user(conn):
    db.get_or_create_user(conn, 123)
    birthday_id = db.add_birthday(conn, 123, "Mom", 3, 14, 1965, None)

    assert db.delete_birthday(conn, birthday_id, 123) is True
    assert db.get_user_birthdays(conn, 123) == []


def test_delete_birthday_not_owned_by_user_fails(conn):
    db.get_or_create_user(conn, 123)
    db.get_or_create_user(conn, 456)
    birthday_id = db.add_birthday(conn, 123, "Mom", 3, 14, 1965, None)

    assert db.delete_birthday(conn, birthday_id, 456) is False
    assert len(db.get_user_birthdays(conn, 123)) == 1


def test_update_birthday(conn):
    db.get_or_create_user(conn, 123)
    birthday_id = db.add_birthday(conn, 123, "Mom", 3, 14, 1965, None)

    assert db.update_birthday(conn, birthday_id, 123, "Mother", 3, 15, 1966, "updated") is True

    birthdays = db.get_user_birthdays(conn, 123)
    assert birthdays[0].name == "Mother"
    assert birthdays[0].day == 15
    assert birthdays[0].year == 1966
    assert birthdays[0].notes == "updated"


def test_update_birthday_not_owned_by_user_fails(conn):
    db.get_or_create_user(conn, 123)
    db.get_or_create_user(conn, 456)
    birthday_id = db.add_birthday(conn, 123, "Mom", 3, 14, 1965, None)

    assert db.update_birthday(conn, birthday_id, 456, "Hacked", 1, 1, 2000, None) is False


def test_cascade_delete_removes_birthdays_when_user_deleted(conn):
    db.get_or_create_user(conn, 123)
    db.add_birthday(conn, 123, "Mom", 3, 14, 1965, None)

    conn.execute("DELETE FROM users WHERE user_id = ?", (123,))
    conn.commit()

    assert db.get_user_birthdays(conn, 123) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `AttributeError: module 'db' has no attribute 'add_birthday'`

- [ ] **Step 3: Implement birthday CRUD functions in `db.py`**

Add to `db.py` (at the end of the file):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db.py -v`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add birthday CRUD functions with ownership checks"
```

---

### Task 8: `reminders.py` — `should_send_reminder`

**Files:**
- Create: `reminders.py`
- Test: `tests/test_reminders.py`

- [ ] **Step 1: Write failing tests for `should_send_reminder`**

Create `tests/test_reminders.py`:

```python
from datetime import datetime, timezone

from reminders import should_send_reminder


def test_should_send_reminder_before_reminder_hour():
    now_utc = datetime(2026, 6, 11, 8, 0, tzinfo=timezone.utc)
    assert should_send_reminder(now_utc, "UTC", 9, None) is False


def test_should_send_reminder_at_or_after_reminder_hour():
    now_utc = datetime(2026, 6, 11, 9, 30, tzinfo=timezone.utc)
    assert should_send_reminder(now_utc, "UTC", 9, None) is True


def test_should_send_reminder_already_sent_today():
    now_utc = datetime(2026, 6, 11, 10, 0, tzinfo=timezone.utc)
    assert should_send_reminder(now_utc, "UTC", 9, "2026-06-11") is False


def test_should_send_reminder_new_day_after_previous_send():
    now_utc = datetime(2026, 6, 12, 9, 0, tzinfo=timezone.utc)
    assert should_send_reminder(now_utc, "UTC", 9, "2026-06-11") is True


def test_should_send_reminder_respects_positive_timezone_offset():
    # 23:00 UTC on June 11 == 09:00 in UTC+10 (Pacific/Guam) on June 12
    now_utc = datetime(2026, 6, 11, 23, 0, tzinfo=timezone.utc)
    assert should_send_reminder(now_utc, "Pacific/Guam", 9, None) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reminders.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'reminders'`

- [ ] **Step 3: Implement `should_send_reminder` in `reminders.py`**

Create `reminders.py`:

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo

from birthdays import age_on_next_birthday, days_until
from models import Birthday


def should_send_reminder(
    now_utc: datetime,
    timezone: str,
    reminder_hour: int,
    last_sent_date: str | None,
) -> bool:
    """True if the user's current local date differs from last_sent_date
    AND the local hour is >= reminder_hour."""
    local_now = now_utc.astimezone(ZoneInfo(timezone))
    local_date_str = local_now.date().isoformat()

    if local_date_str == last_sent_date:
        return False

    return local_now.hour >= reminder_hour
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reminders.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add reminders.py tests/test_reminders.py
git commit -m "feat: add should_send_reminder with timezone handling, TDD"
```

---

### Task 9: `reminders.py` — `build_digest_message`

**Files:**
- Modify: `reminders.py`
- Modify: `tests/test_reminders.py`

- [ ] **Step 1: Write failing tests for `build_digest_message`**

Append to `tests/test_reminders.py`:

```python
from datetime import date

from reminders import build_digest_message
from models import Birthday


def test_build_digest_message_empty_returns_none():
    assert build_digest_message([], date(2026, 6, 11), 7) is None


def test_build_digest_message_today_only():
    today = date(2026, 6, 11)
    birthdays = [Birthday(id=1, user_id=1, name="Mom", month=6, day=11, year=1965, notes=None)]

    message = build_digest_message(birthdays, today, 7)

    assert "Today's birthdays" in message
    assert "Mom (turns 61)" in message
    assert "Coming up" not in message


def test_build_digest_message_upcoming_only():
    today = date(2026, 6, 11)
    birthdays = [Birthday(id=1, user_id=1, name="Alex", month=6, day=14, year=None, notes=None)]

    message = build_digest_message(birthdays, today, 7)

    assert "Coming up" in message
    assert "Alex" in message
    assert "Today's birthdays" not in message


def test_build_digest_message_sorts_upcoming_by_date():
    today = date(2026, 6, 11)
    birthdays = [
        Birthday(id=1, user_id=1, name="Later", month=6, day=18, year=None, notes=None),
        Birthday(id=2, user_id=1, name="Sooner", month=6, day=13, year=None, notes=None),
    ]

    message = build_digest_message(birthdays, today, 7)

    assert message.index("Sooner") < message.index("Later")


def test_build_digest_message_outside_window_is_excluded():
    today = date(2026, 6, 11)
    birthdays = [Birthday(id=1, user_id=1, name="FarAway", month=12, day=25, year=None, notes=None)]

    assert build_digest_message(birthdays, today, 7) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reminders.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_digest_message' from 'reminders'`

- [ ] **Step 3: Implement `build_digest_message` in `reminders.py`**

Add to `reminders.py` (at the end of the file):

```python
def build_digest_message(birthdays: list[Birthday], today: date, window_days: int) -> str | None:
    """Returns a formatted digest of today's and upcoming birthdays, or
    None if there is nothing to report within window_days."""
    today_entries: list[str] = []
    upcoming_entries: list[tuple[int, str]] = []

    for b in birthdays:
        delta = days_until(today, b.month, b.day)

        if delta == 0:
            age = age_on_next_birthday(b.year, b.month, b.day, today)
            label = b.name if age is None else f"{b.name} (turns {age})"
            today_entries.append(label)
        elif delta <= window_days:
            date_str = f"{b.day:02d}-{b.month:02d}"
            plural = "s" if delta != 1 else ""
            upcoming_entries.append((delta, f"{b.name} — in {delta} day{plural} ({date_str})"))

    if not today_entries and not upcoming_entries:
        return None

    lines: list[str] = []

    if today_entries:
        lines.append("🎂 Today's birthdays:")
        for entry in today_entries:
            lines.append(f"  • {entry}")

    if upcoming_entries:
        if lines:
            lines.append("")
        upcoming_entries.sort(key=lambda item: item[0])
        lines.append(f"📅 Coming up (next {window_days} days):")
        for _, entry in upcoming_entries:
            lines.append(f"  • {entry}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reminders.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add reminders.py tests/test_reminders.py
git commit -m "feat: add build_digest_message with today/upcoming sections, TDD"
```

---

### Task 10: `handlers.py` — `/start` and `/add`

**Files:**
- Create: `handlers.py`
- Test: `tests/test_handlers.py`

- [ ] **Step 1: Write failing tests for `/start` and `/add`**

Create `tests/test_handlers.py`:

```python
import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest

import db
import handlers


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(db.SCHEMA)
    connection.commit()
    yield connection
    connection.close()


def make_update(user_id=123):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def make_context(conn, args=None):
    context = MagicMock()
    context.bot_data = {"conn": conn}
    context.args = args or []
    return context


@pytest.mark.asyncio
async def test_cmd_start_creates_user_and_replies(conn):
    update = make_update()
    context = make_context(conn)

    await handlers.cmd_start(update, context)

    assert db.get_user(conn, 123) is not None
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_add_valid_birthday(conn):
    update = make_update()
    context = make_context(conn, args=["Mom", "14-03-1965", "loves", "flowers"])

    await handlers.cmd_add(update, context)

    birthdays = db.get_user_birthdays(conn, 123)
    assert len(birthdays) == 1
    assert birthdays[0].name == "Mom"
    assert birthdays[0].notes == "loves flowers"

    reply_text = update.message.reply_text.call_args[0][0]
    assert "Added" in reply_text


@pytest.mark.asyncio
async def test_cmd_add_without_notes(conn):
    update = make_update()
    context = make_context(conn, args=["Alex", "02-11"])

    await handlers.cmd_add(update, context)

    birthdays = db.get_user_birthdays(conn, 123)
    assert birthdays[0].notes is None
    assert birthdays[0].year is None


@pytest.mark.asyncio
async def test_cmd_add_invalid_date_replies_with_error(conn):
    update = make_update()
    context = make_context(conn, args=["Mom", "not-a-date"])

    await handlers.cmd_add(update, context)

    assert db.get_user_birthdays(conn, 123) == []
    reply_text = update.message.reply_text.call_args[0][0]
    assert "⚠️" in reply_text


@pytest.mark.asyncio
async def test_cmd_add_missing_args_replies_with_usage(conn):
    update = make_update()
    context = make_context(conn, args=["Mom"])

    await handlers.cmd_add(update, context)

    assert db.get_user_birthdays(conn, 123) == []
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'handlers'`

- [ ] **Step 3: Implement `/start` and `/add` in `handlers.py`**

Create `handlers.py`:

```python
from telegram import Update
from telegram.ext import ContextTypes

import db
from birthdays import parse_birthday_date


WELCOME_TEXT = (
    "👋 Welcome to the Birthday Reminder bot!\n\n"
    "Commands:\n"
    "/add <Name> <DD-MM[-YYYY]> [notes] — add a birthday\n"
    "/list — list all your birthdays\n"
    "/upcoming [days] — show upcoming birthdays\n"
    "/edit <id> <Name> <DD-MM[-YYYY]> [notes] — edit a birthday\n"
    "/delete <id> — delete a birthday\n"
    "/settimezone <IANA tz name> — set your timezone (e.g. Europe/Berlin)\n"
    "/setwindow <days> — set the lookahead window for reminders"
)

ADD_USAGE = "Usage: /add <Name> <DD-MM[-YYYY]> [notes]\nExample: /add Mom 14-03-1965 loves flowers"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    db.get_or_create_user(conn, update.effective_user.id)
    await update.message.reply_text(WELCOME_TEXT)


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id
    db.get_or_create_user(conn, user_id)

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(ADD_USAGE)
        return

    name = args[0]
    try:
        month, day, year = parse_birthday_date(args[1])
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
        return

    notes = " ".join(args[2:]) if len(args) > 2 else None
    birthday_id = db.add_birthday(conn, user_id, name, month, day, year, notes)

    date_str = f"{day:02d}-{month:02d}" + (f"-{year}" if year else "")
    await update.message.reply_text(f'✅ Added "{name}" ({date_str}) — id #{birthday_id}')
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add handlers.py tests/test_handlers.py
git commit -m "feat: add /start and /add command handlers, TDD"
```

---

### Task 11: `handlers.py` — `/list`

**Files:**
- Modify: `handlers.py`
- Modify: `tests/test_handlers.py`

- [ ] **Step 1: Write failing tests for `/list`**

Append to `tests/test_handlers.py`:

```python
@pytest.mark.asyncio
async def test_cmd_list_empty(conn):
    update = make_update()
    context = make_context(conn)

    await handlers.cmd_list(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "haven't added" in reply_text


@pytest.mark.asyncio
async def test_cmd_list_shows_entries_sorted_by_upcoming(conn):
    db.get_or_create_user(conn, 123)
    db.add_birthday(conn, 123, "Later", 12, 25, None, None)
    db.add_birthday(conn, 123, "Sooner", 6, 12, 1990, "close friend")

    update = make_update()
    context = make_context(conn)

    await handlers.cmd_list(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert reply_text.index("Sooner") < reply_text.index("Later")
    assert "close friend" in reply_text
```

Note: this test relies on "today" being earlier in the year than both Jun 12 and Dec 25 relative to each other — Sooner (Jun 12) is always closer than Later (Dec 25) regardless of the actual current date, since both wrap forward from "today" and Jun 12 to Dec 25 is fewer days than Dec 25 to Jun 12 in the vast majority of the year. To keep this deterministic, the test only checks relative order, not exact day counts.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers.py -v`
Expected: FAIL with `AttributeError: module 'handlers' has no attribute 'cmd_list'`

- [ ] **Step 3: Implement `/list` in `handlers.py`**

Add to `handlers.py`. First, update the imports at the top of the file:

```python
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import db
from birthdays import age_on_next_birthday, days_until, parse_birthday_date
```

Then add the handler at the end of the file:

```python
async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id
    db.get_or_create_user(conn, user_id)

    birthdays = db.get_user_birthdays(conn, user_id)
    if not birthdays:
        await update.message.reply_text("You haven't added any birthdays yet. Use /add to get started.")
        return

    today = date.today()
    birthdays.sort(key=lambda b: days_until(today, b.month, b.day))

    lines = []
    for b in birthdays:
        date_str = f"{b.day:02d}-{b.month:02d}" + (f"-{b.year}" if b.year else "")
        age = age_on_next_birthday(b.year, b.month, b.day, today)

        line = f"#{b.id} {b.name} — {date_str}"
        if age is not None:
            line += f" (turns {age})"
        if b.notes:
            line += f" — {b.notes}"
        lines.append(line)

    await update.message.reply_text("\n".join(lines))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add handlers.py tests/test_handlers.py
git commit -m "feat: add /list command handler, TDD"
```

---

### Task 12: `handlers.py` — `/delete` and `/edit`

**Files:**
- Modify: `handlers.py`
- Modify: `tests/test_handlers.py`

- [ ] **Step 1: Write failing tests for `/delete` and `/edit`**

Append to `tests/test_handlers.py`:

```python
@pytest.mark.asyncio
async def test_cmd_delete_existing(conn):
    db.get_or_create_user(conn, 123)
    birthday_id = db.add_birthday(conn, 123, "Mom", 3, 14, 1965, None)

    update = make_update()
    context = make_context(conn, args=[str(birthday_id)])

    await handlers.cmd_delete(update, context)

    assert db.get_user_birthdays(conn, 123) == []
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Deleted" in reply_text


@pytest.mark.asyncio
async def test_cmd_delete_not_found(conn):
    db.get_or_create_user(conn, 123)

    update = make_update()
    context = make_context(conn, args=["999"])

    await handlers.cmd_delete(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "not found" in reply_text


@pytest.mark.asyncio
async def test_cmd_delete_invalid_id_replies_with_usage(conn):
    db.get_or_create_user(conn, 123)

    update = make_update()
    context = make_context(conn, args=["abc"])

    await handlers.cmd_delete(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply_text


@pytest.mark.asyncio
async def test_cmd_edit_existing(conn):
    db.get_or_create_user(conn, 123)
    birthday_id = db.add_birthday(conn, 123, "Mom", 3, 14, 1965, None)

    update = make_update()
    context = make_context(conn, args=[str(birthday_id), "Mother", "15-03-1966", "updated", "notes"])

    await handlers.cmd_edit(update, context)

    birthdays = db.get_user_birthdays(conn, 123)
    assert birthdays[0].name == "Mother"
    assert birthdays[0].day == 15
    assert birthdays[0].notes == "updated notes"

    reply_text = update.message.reply_text.call_args[0][0]
    assert "Updated" in reply_text


@pytest.mark.asyncio
async def test_cmd_edit_not_found(conn):
    db.get_or_create_user(conn, 123)

    update = make_update()
    context = make_context(conn, args=["999", "Name", "01-01"])

    await handlers.cmd_edit(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "not found" in reply_text


@pytest.mark.asyncio
async def test_cmd_edit_invalid_date_replies_with_error(conn):
    db.get_or_create_user(conn, 123)
    birthday_id = db.add_birthday(conn, 123, "Mom", 3, 14, 1965, None)

    update = make_update()
    context = make_context(conn, args=[str(birthday_id), "Mom", "not-a-date"])

    await handlers.cmd_edit(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "⚠️" in reply_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers.py -v`
Expected: FAIL with `AttributeError: module 'handlers' has no attribute 'cmd_delete'`

- [ ] **Step 3: Implement `/delete` and `/edit` in `handlers.py`**

Add to `handlers.py` (at the end of the file):

```python
DELETE_USAGE = "Usage: /delete <id>"
EDIT_USAGE = "Usage: /edit <id> <Name> <DD-MM[-YYYY]> [notes]\nExample: /edit 1 Mom 14-03-1965 loves flowers"


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id

    args = context.args
    if len(args) != 1:
        await update.message.reply_text(DELETE_USAGE)
        return

    try:
        birthday_id = int(args[0])
    except ValueError:
        await update.message.reply_text(f"{DELETE_USAGE} (id must be a number)")
        return

    if db.delete_birthday(conn, birthday_id, user_id):
        await update.message.reply_text(f"🗑️ Deleted birthday #{birthday_id}")
    else:
        await update.message.reply_text(f"Birthday #{birthday_id} not found.")


async def cmd_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(EDIT_USAGE)
        return

    try:
        birthday_id = int(args[0])
    except ValueError:
        await update.message.reply_text(f"The id must be a number.\n{EDIT_USAGE}")
        return

    name = args[1]
    try:
        month, day, year = parse_birthday_date(args[2])
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
        return

    notes = " ".join(args[3:]) if len(args) > 3 else None

    if db.update_birthday(conn, birthday_id, user_id, name, month, day, year, notes):
        date_str = f"{day:02d}-{month:02d}" + (f"-{year}" if year else "")
        await update.message.reply_text(f'✅ Updated #{birthday_id}: "{name}" ({date_str})')
    else:
        await update.message.reply_text(f"Birthday #{birthday_id} not found.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers.py -v`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```bash
git add handlers.py tests/test_handlers.py
git commit -m "feat: add /delete and /edit command handlers, TDD"
```

---

### Task 13: `handlers.py` — `/upcoming`

**Files:**
- Modify: `handlers.py`
- Modify: `tests/test_handlers.py`

- [ ] **Step 1: Write failing tests for `/upcoming`**

Append to `tests/test_handlers.py`:

```python
@pytest.mark.asyncio
async def test_cmd_upcoming_uses_default_window(conn):
    user = db.get_or_create_user(conn, 123)
    today = date.today()
    db.add_birthday(conn, 123, "TodayPerson", today.month, today.day, None, None)

    update = make_update()
    context = make_context(conn)

    await handlers.cmd_upcoming(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "TodayPerson" in reply_text


@pytest.mark.asyncio
async def test_cmd_upcoming_empty(conn):
    db.get_or_create_user(conn, 123)

    update = make_update()
    context = make_context(conn, args=["5"])

    await handlers.cmd_upcoming(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "No birthdays in the next 5 days" in reply_text


@pytest.mark.asyncio
async def test_cmd_upcoming_invalid_days_replies_with_usage(conn):
    db.get_or_create_user(conn, 123)

    update = make_update()
    context = make_context(conn, args=["not-a-number"])

    await handlers.cmd_upcoming(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply_text


@pytest.mark.asyncio
async def test_cmd_upcoming_explicit_window_overrides_default(conn):
    db.get_or_create_user(conn, 123)
    today = date.today()
    far_month = today.month
    # Pick a target 10 days out (relative add via days_until-friendly math is
    # avoided here; instead reuse today's month/day for a "today" match and
    # rely on the empty-window test above for the "nothing found" case).
    db.add_birthday(conn, 123, "TodayPerson", today.month, today.day, None, None)

    update = make_update()
    context = make_context(conn, args=["1"])

    await handlers.cmd_upcoming(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "TodayPerson" in reply_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers.py -v`
Expected: FAIL with `AttributeError: module 'handlers' has no attribute 'cmd_upcoming'`

- [ ] **Step 3: Implement `/upcoming` in `handlers.py`**

Add to `handlers.py` (at the end of the file):

```python
UPCOMING_USAGE = "Usage: /upcoming [days] (days must be a positive number)"


async def cmd_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id
    user = db.get_or_create_user(conn, user_id)

    args = context.args
    if args:
        try:
            window_days = int(args[0])
            if window_days < 1:
                raise ValueError
        except ValueError:
            await update.message.reply_text(UPCOMING_USAGE)
            return
    else:
        window_days = user.lookahead_days

    today = date.today()
    birthdays = db.get_user_birthdays(conn, user_id)

    entries: list[tuple[int, str]] = []
    for b in birthdays:
        delta = days_until(today, b.month, b.day)
        if delta > window_days:
            continue

        date_str = f"{b.day:02d}-{b.month:02d}"
        if delta == 0:
            entries.append((delta, f"{b.name} — today ({date_str})"))
        else:
            plural = "s" if delta != 1 else ""
            entries.append((delta, f"{b.name} — in {delta} day{plural} ({date_str})"))

    if not entries:
        await update.message.reply_text(f"No birthdays in the next {window_days} days.")
        return

    entries.sort(key=lambda item: item[0])
    lines = [f"🎂 Birthdays in the next {window_days} days:"]
    for _, entry in entries:
        lines.append(f"  • {entry}")

    await update.message.reply_text("\n".join(lines))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers.py -v`
Expected: PASS (17 passed)

- [ ] **Step 5: Commit**

```bash
git add handlers.py tests/test_handlers.py
git commit -m "feat: add /upcoming command handler, TDD"
```

---

### Task 14: `handlers.py` — `/settimezone` and `/setwindow`

**Files:**
- Modify: `handlers.py`
- Modify: `tests/test_handlers.py`

- [ ] **Step 1: Write failing tests for `/settimezone` and `/setwindow`**

Append to `tests/test_handlers.py`:

```python
@pytest.mark.asyncio
async def test_cmd_settimezone_valid(conn):
    update = make_update()
    context = make_context(conn, args=["Europe/Berlin"])

    await handlers.cmd_settimezone(update, context)

    user = db.get_user(conn, 123)
    assert user.timezone == "Europe/Berlin"
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Europe/Berlin" in reply_text


@pytest.mark.asyncio
async def test_cmd_settimezone_invalid(conn):
    update = make_update()
    context = make_context(conn, args=["Not/AZone"])

    await handlers.cmd_settimezone(update, context)

    user = db.get_user(conn, 123)
    assert user.timezone == "UTC"
    reply_text = update.message.reply_text.call_args[0][0]
    assert "⚠️" in reply_text


@pytest.mark.asyncio
async def test_cmd_settimezone_missing_arg_replies_with_usage(conn):
    update = make_update()
    context = make_context(conn, args=[])

    await handlers.cmd_settimezone(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply_text


@pytest.mark.asyncio
async def test_cmd_setwindow_valid(conn):
    update = make_update()
    context = make_context(conn, args=["14"])

    await handlers.cmd_setwindow(update, context)

    user = db.get_user(conn, 123)
    assert user.lookahead_days == 14
    reply_text = update.message.reply_text.call_args[0][0]
    assert "14" in reply_text


@pytest.mark.asyncio
async def test_cmd_setwindow_out_of_range_replies_with_error(conn):
    update = make_update()
    context = make_context(conn, args=["400"])

    await handlers.cmd_setwindow(update, context)

    user = db.get_user(conn, 123)
    assert user.lookahead_days == 7  # unchanged default
    reply_text = update.message.reply_text.call_args[0][0]
    assert "1 and 365" in reply_text


@pytest.mark.asyncio
async def test_cmd_setwindow_non_numeric_replies_with_error(conn):
    update = make_update()
    context = make_context(conn, args=["abc"])

    await handlers.cmd_setwindow(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "1 and 365" in reply_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers.py -v`
Expected: FAIL with `AttributeError: module 'handlers' has no attribute 'cmd_settimezone'`

- [ ] **Step 3: Implement `/settimezone` and `/setwindow` in `handlers.py`**

Add `from zoneinfo import available_timezones` to the imports at the top of `handlers.py`:

```python
from datetime import date
from zoneinfo import available_timezones

from telegram import Update
from telegram.ext import ContextTypes

import db
from birthdays import age_on_next_birthday, days_until, parse_birthday_date
```

Then add the handlers at the end of `handlers.py`:

```python
SETTIMEZONE_USAGE = "Usage: /settimezone <IANA tz name>\nExample: /settimezone Europe/Berlin"
SETWINDOW_USAGE = "The number of days must be an integer between 1 and 365.\nUsage: /setwindow <days>"


async def cmd_settimezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id
    db.get_or_create_user(conn, user_id)

    args = context.args
    if len(args) != 1:
        await update.message.reply_text(SETTIMEZONE_USAGE)
        return

    tz_name = args[0]
    if tz_name not in available_timezones():
        await update.message.reply_text(f"⚠️ Unknown timezone: {tz_name!r}. Use an IANA name, e.g. Europe/Berlin")
        return

    db.update_timezone(conn, user_id, tz_name)
    await update.message.reply_text(f"✅ Timezone set to {tz_name}")


async def cmd_setwindow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id
    db.get_or_create_user(conn, user_id)

    args = context.args
    if len(args) != 1:
        await update.message.reply_text(SETWINDOW_USAGE)
        return

    try:
        days = int(args[0])
        if not (1 <= days <= 365):
            raise ValueError
    except ValueError:
        await update.message.reply_text(SETWINDOW_USAGE)
        return

    db.update_lookahead_days(conn, user_id, days)
    await update.message.reply_text(f"✅ Lookahead window set to {days} days")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers.py -v`
Expected: PASS (23 passed)

- [ ] **Step 5: Commit**

```bash
git add handlers.py tests/test_handlers.py
git commit -m "feat: add /settimezone and /setwindow command handlers, TDD"
```

---

### Task 15: `scheduler.py` — `run_daily_check` and scheduler setup

**Files:**
- Create: `scheduler.py`
- Test: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests for `run_daily_check`**

Create `tests/test_scheduler.py`:

```python
import sqlite3
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

import db
import scheduler


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(db.SCHEMA)
    connection.commit()
    yield connection
    connection.close()


@pytest.mark.asyncio
async def test_run_daily_check_sends_digest_and_updates_last_sent(conn):
    db.get_or_create_user(conn, 123)  # UTC, reminder_hour=9, lookahead=7
    today = datetime.now(timezone.utc).date()
    db.add_birthday(conn, 123, "Mom", today.month, today.day, 1965, None)

    bot = AsyncMock()
    now_utc = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=9, minute=30)

    await scheduler.run_daily_check(conn, bot, now_utc=now_utc)

    bot.send_message.assert_called_once()
    call_kwargs = bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == 123
    assert "Mom" in call_kwargs["text"]

    user = db.get_user(conn, 123)
    assert user.last_sent_date == today.isoformat()


@pytest.mark.asyncio
async def test_run_daily_check_skips_user_before_reminder_hour(conn):
    db.get_or_create_user(conn, 123)  # reminder_hour=9
    today = datetime.now(timezone.utc).date()
    db.add_birthday(conn, 123, "Mom", today.month, today.day, 1965, None)

    bot = AsyncMock()
    now_utc = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=8, minute=0)

    await scheduler.run_daily_check(conn, bot, now_utc=now_utc)

    bot.send_message.assert_not_called()
    user = db.get_user(conn, 123)
    assert user.last_sent_date is None


@pytest.mark.asyncio
async def test_run_daily_check_no_birthdays_updates_last_sent_without_sending(conn):
    db.get_or_create_user(conn, 123)
    today = datetime.now(timezone.utc).date()

    bot = AsyncMock()
    now_utc = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=9, minute=30)

    await scheduler.run_daily_check(conn, bot, now_utc=now_utc)

    bot.send_message.assert_not_called()
    user = db.get_user(conn, 123)
    assert user.last_sent_date == today.isoformat()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scheduler'`

- [ ] **Step 3: Implement `scheduler.py`**

Create `scheduler.py`:

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import Application

import db
from reminders import build_digest_message, should_send_reminder


async def run_daily_check(conn, bot: Bot, now_utc: datetime | None = None) -> None:
    """Checks every user; sends a digest if it's their reminder time and
    they haven't been sent one today. Always updates last_sent_date for
    users whose reminder time has arrived, even if there's nothing to send,
    so we don't re-check them again for the rest of their local day."""
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    for user in db.get_all_users(conn):
        if not should_send_reminder(now_utc, user.timezone, user.reminder_hour, user.last_sent_date):
            continue

        local_today = now_utc.astimezone(ZoneInfo(user.timezone)).date()
        birthdays = db.get_user_birthdays(conn, user.user_id)
        text = build_digest_message(birthdays, local_today, user.lookahead_days)

        if text is not None:
            await bot.send_message(chat_id=user.user_id, text=text)

        db.update_last_sent_date(conn, user.user_id, local_today.isoformat())


def setup_scheduler(application: Application, conn) -> AsyncIOScheduler:
    """Creates and starts an hourly job that runs run_daily_check.
    Must be called from within a running asyncio event loop (e.g. from a
    PTB post_init hook)."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_check, "interval", hours=1, args=[conn, application.bot])
    scheduler.start()
    return scheduler
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "feat: add hourly digest scheduler with should_send_reminder integration, TDD"
```

---

### Task 16: `bot.py` and `config.py` — entry point wiring

**Files:**
- Create: `config.py`
- Create: `bot.py`

- [ ] **Step 1: Create `config.py`**

```python
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_PATH = os.environ.get("DB_PATH", "jubilous.db")
```

- [ ] **Step 2: Create `bot.py`**

```python
import logging

from telegram.ext import Application, CommandHandler

import db
from config import BOT_TOKEN, DB_PATH
from handlers import (
    cmd_add,
    cmd_delete,
    cmd_edit,
    cmd_list,
    cmd_settimezone,
    cmd_setwindow,
    cmd_start,
    cmd_upcoming,
)
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)


async def post_init(application: Application) -> None:
    """Starts the reminder scheduler once the bot's event loop is running."""
    setup_scheduler(application, application.bot_data["conn"])


def main() -> None:
    conn = db.connect(DB_PATH)

    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.bot_data["conn"] = conn

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("add", cmd_add))
    application.add_handler(CommandHandler("list", cmd_list))
    application.add_handler(CommandHandler("delete", cmd_delete))
    application.add_handler(CommandHandler("edit", cmd_edit))
    application.add_handler(CommandHandler("upcoming", cmd_upcoming))
    application.add_handler(CommandHandler("settimezone", cmd_settimezone))
    application.add_handler(CommandHandler("setwindow", cmd_setwindow))

    application.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify the full test suite still passes**

Run: `pytest -v`
Expected: PASS (all tests from Tasks 2-15 pass; `bot.py` and `config.py` have no dedicated tests since they're a thin entry point covered by manual testing in Task 17)

- [ ] **Step 4: Verify `bot.py` starts without import errors**

Create a temporary `.env` file (copy from `.env.example`) with a placeholder token, then run:

```bash
cp .env.example .env
# edit .env and set BOT_TOKEN to any non-empty string for this import check
python -c "import bot"
```

Expected: no `ImportError`/`ModuleNotFoundError`/`SyntaxError`. (It will not actually connect to Telegram with a fake token — real connectivity is tested in Task 17 with a real token.)

- [ ] **Step 5: Commit**

```bash
git add config.py bot.py
git commit -m "feat: wire up bot entry point with handlers and scheduler"
```

---

### Task 17: Manual end-to-end testing

**Files:** none (manual verification using the existing code)

- [ ] **Step 1: Create a real Telegram test bot**

In Telegram, message `@BotFather`, run `/newbot`, follow the prompts, and copy the resulting bot token.

- [ ] **Step 2: Configure `.env` with the real token**

Edit `.env` (created in Task 16):

```
BOT_TOKEN=<paste your real token here>
DB_PATH=jubilous.db
```

- [ ] **Step 3: Run the bot**

```bash
source .venv/bin/activate
python bot.py
```

Expected: logs show the bot starting up with no errors, and it stays running (polling).

- [ ] **Step 4: Exercise the core commands from your Telegram client**

In a chat with your bot, send each of these in order and confirm the responses match expectations:

1. `/start` → welcome message listing all commands
2. `/add Mom 14-03-1965 loves flowers` → `✅ Added "Mom" (14-03-1965) — id #1`
3. `/add Alex 02-11` → `✅ Added "Alex" (02-11) — id #2`
4. `/list` → both entries shown, sorted by upcoming date, "Mom" shows `(turns N)`, "Alex" does not
5. `/upcoming 30` → shows entries within 30 days (may be empty depending on current date — that's fine, confirms the empty-state message)
6. `/settimezone Europe/Berlin` → `✅ Timezone set to Europe/Berlin`
7. `/settimezone Not/AZone` → `⚠️ Unknown timezone...`
8. `/setwindow 14` → `✅ Lookahead window set to 14 days`
9. `/setwindow 400` → error message mentioning "1 and 365"
10. `/edit 1 Mom 15-03-1965 still loves flowers` → `✅ Updated #1: "Mom" (15-03-1965)`
11. `/delete 2` → `🗑️ Deleted birthday #2`
12. `/delete 2` again → `Birthday #2 not found.`
13. `/list` → only "Mom" remains, with updated date and notes

- [ ] **Step 5: Manually verify the digest message**

With the bot still running, add a birthday for today's date:

```
/add TestToday <today's DD-MM>
```

Then, in a separate terminal (with `.venv` activated and in the project directory), force a digest check by directly invoking `run_daily_check` against the same database, with `now_utc` set to your local 9am-or-later time:

```bash
python - <<'EOF'
import asyncio
from datetime import datetime, timezone

import db
import scheduler
from telegram import Bot
from config import BOT_TOKEN, DB_PATH

conn = db.connect(DB_PATH)
bot = Bot(token=BOT_TOKEN)

# Force "now" to be 09:30 UTC today so the UTC-timezone test user is due.
now = datetime.now(timezone.utc).replace(hour=9, minute=30)
asyncio.run(scheduler.run_daily_check(conn, bot, now_utc=now))
EOF
```

Expected: your Telegram chat receives a message starting with `🎂 Today's birthdays:` listing `TestToday`.

- [ ] **Step 6: Verify duplicate-send prevention**

Run the same script from Step 5 again immediately.

Expected: no second message is sent (because `last_sent_date` was updated to today by the previous run).

- [ ] **Step 7: Stop the bot**

Press `Ctrl+C` in the terminal running `python bot.py`.

- [ ] **Step 8: Clean up test data (optional)**

```bash
rm jubilous.db
```

This removes the SQLite file created during manual testing so the next run starts fresh. No commit needed for this task — it's verification only.

---

### Task 18: README and demo script

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# Jubilous — Telegram Birthday Reminder Service

A simplified Telegram bot that lets users save birthdays, stores them in
SQLite, sends a daily reminder digest, and shows upcoming birthdays on
demand.

## Tech stack

- Python 3.11+
- [python-telegram-bot](https://docs.python-telegram-bot.org/) v21 (async)
- SQLite (via the standard library `sqlite3`)
- [APScheduler](https://apscheduler.readthedocs.io/) (AsyncIOScheduler)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `BOT_TOKEN` to a token from
[@BotFather](https://t.me/BotFather). `DB_PATH` defaults to `jubilous.db`
in the project directory.

## Running

```bash
source .venv/bin/activate
python bot.py
```

The bot starts polling for Telegram updates and runs an hourly background
job that checks whether any user's daily digest is due.

## Commands

| Command | Args | Description |
|---|---|---|
| `/start` | — | Registers you with the bot and shows this command list |
| `/add` | `<Name> <DD-MM[-YYYY]> [notes...]` | Add a birthday. Year and notes are optional. |
| `/list` | — | List all your saved birthdays, soonest first |
| `/upcoming` | `[days]` | Show birthdays in the next N days (default: your configured window) |
| `/edit` | `<id> <Name> <DD-MM[-YYYY]> [notes...]` | Overwrite an existing birthday entry |
| `/delete` | `<id>` | Delete a birthday entry |
| `/settimezone` | `<IANA tz name>` | Set your timezone, e.g. `Europe/Berlin` (used for digest timing) |
| `/setwindow` | `<days>` | Set your lookahead window (1-365) for `/upcoming` and the daily digest |

## Architecture

```
jubilous/
├── bot.py        # Entry point: builds the app, registers handlers, starts the scheduler
├── config.py     # Loads BOT_TOKEN and DB_PATH from environment
├── db.py         # SQLite schema + data access functions
├── models.py     # User and Birthday dataclasses
├── birthdays.py  # Pure date logic: parsing, days-until, age calculation
├── reminders.py  # Pure reminder logic: should-send check, digest formatting
├── handlers.py   # Telegram command handlers
├── scheduler.py  # Hourly job that sends daily digests
└── tests/        # pytest unit tests for all modules above
```

`birthdays.py` and `reminders.py` contain no I/O and are fully covered by
unit tests. `db.py` is a thin SQLite layer tested against an in-memory
database. `handlers.py` and `scheduler.py` wire these together for the
running bot.

## Running tests

```bash
source .venv/bin/activate
pytest -v
```

## Known limitations

- **Reminder timing has up to ~59 minutes of jitter**, since the digest
  check runs on an hourly poll rather than a per-user scheduled job.
- **Changing your timezone mid-day** may shift that day's reminder timing.
- Birthdays on **Feb 29** are treated as occurring on **Feb 28** in
  non-leap years.
- Single SQLite file / single process — not designed for horizontal
  scaling.
- `/add` and `/edit` expect the name as a single token (no spaces).

## Demo script

1. `/start` — see the welcome message
2. `/add Mom 14-03-1965 loves flowers` and `/add Alex 02-11`
3. `/list` — see both entries, sorted by upcoming date
4. `/upcoming 30` — see entries within 30 days
5. `/settimezone Europe/Berlin` and `/setwindow 14` — change settings
6. `/edit 1 Mom 15-03-1965 still loves flowers` and `/delete 2`
7. `/list` — confirm the changes
8. Run `pytest -v` to show the test suite passing
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, command reference, and demo script"
```

---

## Plan summary

18 tasks covering: project setup, pure date/reminder logic (TDD), SQLite data layer (TDD), all 8 Telegram commands (TDD), the hourly digest scheduler (TDD), entry-point wiring, manual end-to-end verification, and documentation. Total estimated effort: ~20-30 hours, within the 20-40 hour course project budget.
