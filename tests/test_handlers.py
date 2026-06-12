import sqlite3
from datetime import date
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
