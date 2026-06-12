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
