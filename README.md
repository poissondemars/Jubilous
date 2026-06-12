# Jubilous — Telegram Birthday Reminder Service

A simplified Telegram bot that lets users save birthdays, stores them in
SQLite, sends a daily reminder digest, and shows upcoming birthdays on
demand.

## Tech stack

- Python 3.9+
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
