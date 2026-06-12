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
