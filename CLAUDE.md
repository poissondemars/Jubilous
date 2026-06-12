# Jubilous — CLAUDE.md

Telegram Birthday Reminder Service. Python, python-telegram-bot v21 (async), SQLite, APScheduler.

## Conventions

- Every module starts with `from __future__ import annotations` (needed for `X | None` / `list[...]` syntax on Python 3.9).
- Pure logic lives in `birthdays.py` and `reminders.py` — no DB or Telegram calls, fully unit-testable.
- `db.py` is a thin SQLite data-access layer: one function per query, parameterized queries only.
- `handlers.py` is thin glue: parse `context.args` → call `birthdays.py`/`db.py` → format reply.
- `scheduler.py` wires the hourly `run_daily_check` job; `bot.py` is the entry point.

## Setup & running

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set BOT_TOKEN
python bot.py
```

## Tests

```bash
source .venv/bin/activate
pytest -v
```

TDD workflow: write failing test → verify failure → implement → verify pass → commit.

## Notes

- `.env` and `*.db` are gitignored — never commit real bot tokens or test databases.
- See `README.md` for command reference and demo script, and `docs/superpowers/specs/` and `docs/superpowers/plans/` for the design spec and implementation plan.
