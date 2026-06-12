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
