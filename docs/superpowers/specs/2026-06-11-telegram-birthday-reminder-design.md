# Telegram Birthday Reminder Service — Design Spec

Date: 2026-06-11
Status: Approved (pending implementation plan)

## 1. Overview

A simplified version of "Jubilous": a Telegram bot that lets users save
birthdays, stores them in SQLite, sends a daily reminder digest, and shows
upcoming birthdays on demand. Built as a 20-40 hour Python course project.

Tech stack: Python, `python-telegram-bot` (v20, async), SQLite (`sqlite3`),
APScheduler (`AsyncIOScheduler`).

## 2. MVP Scope

### In scope
- Telegram bot with commands: `/start`, `/add`, `/list`, `/delete`, `/edit`,
  `/upcoming`, `/settimezone`, `/setwindow`
- SQLite storage for users, birthdays, and per-user settings (timezone,
  lookahead window, reminder hour, last sent date)
- Hourly APScheduler job that sends a daily digest (today's + upcoming
  birthdays within the user's window) to each user at ~their local reminder
  hour
- Per-user timezone (IANA tz names via `zoneinfo`) and configurable
  lookahead window

### Out of scope
- Recurring/snoozable reminders, multiple reminders per day
- Group chat support (one-on-one chats only)
- Conversational multi-step add flow (all commands are single-message with
  args)
- Authentication beyond Telegram's own `user_id`
- Localization / multi-language
- Web UI / admin dashboard
- Per-command configurable reminder hour (`/setreminderhour`) — schema
  supports it, but no command exposes it in MVP

## 3. Product Specification

### User flows

**`/start`** (no args)
- Creates a `users` row if one doesn't exist, with defaults:
  `timezone='UTC'`, `lookahead_days=7`, `reminder_hour=9`,
  `last_sent_date=NULL`.
- Replies with a welcome message and command summary.

**`/add <Name> <DD-MM[-YYYY]> [notes...]`**
- Parses the date (`DD-MM` or `DD-MM-YYYY`). Year is optional.
- Inserts a row into `birthdays` for this user.
- Reply: `✅ Added "Name" (DD-MM[-YYYY]) — id #N`
- On parse error: usage hint with example.

**`/list`** (no args)
- Lists all birthdays for the user, sorted by days-until-next-occurrence
  (soonest first).
- Format per line: `#id Name — DD Mon [(turns N)] [— notes]`
- Empty list → "You haven't added any birthdays yet. Use /add to get
  started."

**`/delete <id>`**
- Deletes the birthday with that id, only if it belongs to the requesting
  user.
- Reply: confirmation, or "Birthday #id not found." if missing/not owned.

**`/edit <id> <Name> <DD-MM[-YYYY]> [notes...]`**
- Full overwrite of `name`, `month`, `day`, `year`, `notes` for that id, only
  if owned by the requesting user.
- Reply: confirmation, or "Birthday #id not found."

**`/upcoming [days]`**
- Lists birthdays occurring within the next `days` (inclusive of today).
  Defaults to the user's `lookahead_days` setting if `days` omitted.
- Sorted by date (soonest first).
- Empty → "No birthdays in the next N days."

**`/settimezone <IANA tz name>`**
- Validates against `zoneinfo.available_timezones()`.
- Updates `users.timezone`.
- Invalid → error message with example (`Europe/Berlin`).

**`/setwindow <days>`**
- Validates integer in range 1–365.
- Updates `users.lookahead_days`.

### Daily digest (automated)
- Sent at most once per local calendar day, around the user's
  `reminder_hour` (local time, default 9).
- Content:
  - "Today's birthdays" section — entries where `days_until == 0`
  - "Coming up (next N days)" section — entries where
    `0 < days_until <= lookahead_days`
  - If a section is empty, it's omitted entirely.
  - If both sections are empty, **no message is sent** (but
    `last_sent_date` is still updated, so the check doesn't re-run for the
    rest of that local day).

### Error handling
- Invalid date format, invalid timezone, invalid/missing/non-numeric args →
  friendly error message with usage example. No unhandled exceptions /
  crashes.
- Operating on a non-existent or not-owned birthday id → "not found"
  message (no information leak about other users' data).

### Date parsing conventions
- Accepted formats: `DD-MM` or `DD-MM-YYYY` (day-first, unambiguous).
- `notes` is everything in `context.args` after the date token, rejoined
  with single spaces.

### Feb 29 handling
- For a birthday stored as Feb 29, in a non-leap year it is treated as
  occurring on **Feb 28** for the purposes of `days_until` / digest
  inclusion.

## 4. Technical Design

### Module layout

```
jubilous/
├── bot.py        # Entry point: builds Application, registers handlers, starts scheduler
├── db.py         # SQLite connection, schema setup, CRUD functions
├── models.py     # Dataclasses: User, Birthday
├── handlers.py   # Telegram command handlers
├── birthdays.py  # Pure logic: date parsing, days_until, sorting, age calc
├── reminders.py  # Pure logic: should_send_reminder, build_digest_message
├── scheduler.py  # APScheduler setup, hourly job -> reminders.run_daily_check
├── config.py     # Env-based config (BOT_TOKEN, DB_PATH)
└── tests/
    ├── test_birthdays.py
    ├── test_reminders.py
    ├── test_db.py
    └── test_handlers.py
```

### Principles
- **Pure logic separated from I/O.** `birthdays.py` and `reminders.py`
  contain no DB or Telegram calls — operate on plain Python values
  (dates, dataclasses). This is the TDD-first surface.
- **`db.py`** is a thin data-access layer: one function per query
  (`get_user_birthdays`, `add_birthday`, `update_birthday`,
  `delete_birthday`, `get_all_users`, `update_last_sent_date`, etc.). Uses
  plain `sqlite3` with parameterized queries and a single shared
  connection.
- **`handlers.py`** is glue: parses `context.args`, calls into
  `birthdays.py` / `db.py`, formats replies. Kept thin.
- **`scheduler.py`** wires one `AsyncIOScheduler` interval job (hourly) to
  `reminders.run_daily_check(db, bot)`.

### Data flow — digest job
1. Hourly job fires → `run_daily_check(db, bot)`
2. For each user (`db.get_all_users()`):
   a. Compute `now_utc = datetime.now(timezone.utc)`
   b. `should_send_reminder(now_utc, user.timezone, user.reminder_hour,
      user.last_sent_date)` → bool
   c. If true:
      - `local_today = now_utc.astimezone(ZoneInfo(user.timezone)).date()`
      - `birthdays = db.get_user_birthdays(user.user_id)`
      - `text = build_digest_message(birthdays, local_today,
        user.lookahead_days)`
      - If `text is not None`: send via `bot.send_message`
      - `db.update_last_sent_date(user.user_id, local_today.isoformat())`
        (unconditionally, even if `text is None`)

## 5. SQLite Schema

```sql
CREATE TABLE users (
    user_id         INTEGER PRIMARY KEY,   -- Telegram user_id / chat_id
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    lookahead_days  INTEGER NOT NULL DEFAULT 7,
    reminder_hour   INTEGER NOT NULL DEFAULT 9,
    last_sent_date  TEXT,                  -- ISO date 'YYYY-MM-DD', NULL until first send
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE birthdays (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    month       INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    day         INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
    year        INTEGER,             -- nullable
    notes       TEXT,                -- nullable
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_birthdays_user_id ON birthdays(user_id);
```

Notes:
- `month`/`day` stored separately to support year-less birthdays and Feb 29
  without faking a year.
- `reminder_hour` is present in the schema with a default of 9 but has no
  command to change it in MVP (extension point for a stretch goal).
- `last_sent_date` as ISO text simplifies comparison/reset.
- Cascade delete on `birthdays` if a user row is ever removed.

## 6. Scheduler / Reminder Design

### Pure functions (`reminders.py`)

```python
def should_send_reminder(
    now_utc: datetime,
    timezone: str,
    reminder_hour: int,
    last_sent_date: str | None,
) -> bool:
    """True if the user's current local date differs from last_sent_date
    AND the local hour is >= reminder_hour."""

def build_digest_message(
    birthdays: list[Birthday],
    today: date,
    window_days: int,
) -> str | None:
    """Returns formatted digest text, or None if nothing today/upcoming."""
```

### Pure functions (`birthdays.py`)

```python
def parse_birthday_date(text: str) -> tuple[int, int, int | None]:
    """Parses 'DD-MM' or 'DD-MM-YYYY' -> (month, day, year|None). Raises
    ValueError on invalid input."""

def days_until(today: date, month: int, day: int) -> int:
    """Days from today until next occurrence of month/day (0-365).
    Feb 29 in a non-leap target year is treated as Feb 28."""

def age_on_next_birthday(year: int | None, month: int, day: int, today: date) -> int | None:
    """Returns the age the person turns on their next birthday, or None if
    year is unknown."""
```

### Scheduler wiring (`scheduler.py`)
- `AsyncIOScheduler` (compatible with PTB v20's asyncio loop)
- `scheduler.add_job(run_daily_check, 'interval', hours=1, args=[db, bot])`
- Started during bot startup (e.g. PTB `post_init` hook), stopped on
  shutdown.

### Digest message format
```
🎂 Today's birthdays:
  • Mom (turns 61)

📅 Coming up (next 7 days):
  • Alex — in 3 days (02-11)
```
- Either section omitted if empty; whole message `None` if both empty.

### Known limitations (documented in README)
- Reminder timing has up to ~59 min jitter due to hourly polling.
- Changing timezone mid-day may shift that day's reminder timing.
- Single SQLite file / single process — not designed for horizontal
  scaling.

## 7. Implementation Plan (high-level)

A detailed, 30-90-minute-task breakdown will be produced separately via the
`writing-plans` skill. Rough phases:

1. Project setup (repo structure, `config.py`, dependencies, `.env`)
2. DB layer (`db.py`, schema, CRUD) + tests
3. Pure birthday logic (`birthdays.py`) — TDD
4. Pure reminder logic (`reminders.py`) — TDD
5. Bot handlers: CRUD commands (`/start`, `/add`, `/list`, `/delete`,
   `/edit`)
6. Bot handlers: query/settings commands (`/upcoming`, `/settimezone`,
   `/setwindow`)
7. Scheduler wiring (`scheduler.py`, `run_daily_check`, integration into
   `bot.py`)
8. End-to-end manual testing
9. README + demo prep

## 8. Testing Plan

- **Unit tests (pytest, TDD)** for `birthdays.py` and `reminders.py`:
  - `days_until`: normal dates, today == birthday (→0), Feb 29 handling,
    year wraparound
  - `should_send_reminder`: before/after reminder hour, already-sent-today,
    timezone edge cases (UTC+12, UTC-12)
  - `build_digest_message`: empty / today-only / upcoming-only / both,
    sorting
  - `parse_birthday_date`: valid `DD-MM`, `DD-MM-YYYY`, invalid formats
    raise `ValueError`
- **DB layer tests**: temporary SQLite file per test; CRUD round-trips,
  cascade delete, ownership checks (user A cannot delete/edit user B's
  birthday)
- **Handler tests**: mocked `Update`/`Context` objects (or PTB test
  utilities) verifying parsing → DB calls → reply text, happy + error paths
- **Manual/integration testing**: run against a real test bot token,
  execute the full demo script (Section 9)

## 9. README / Demo Plan

### README contents
- Project overview ("simplified Jubilous")
- Setup instructions (venv, `pip install -r requirements.txt`, `.env` with
  `BOT_TOKEN`)
- Run instructions (`python bot.py`)
- Command reference table (Section 3)
- Architecture description (module list + responsibilities)
- Known limitations (Section 6)

### Demo script
1. `/start` → welcome message
2. `/add` a few birthdays: one "today" (for demo purposes), one with a
   year, one without
3. `/list` → formatted output
4. `/upcoming 30` → filtered/sorted output
5. `/settimezone` + `/setwindow` → show settings affect `/upcoming`
6. `/edit` and `/delete` → management
7. Manually trigger `run_daily_check` (or adjust `last_sent_date`/system
   clock) → show digest arriving
8. Brief code walkthrough + show a passing unit test
