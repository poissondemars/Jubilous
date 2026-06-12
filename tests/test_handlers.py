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
