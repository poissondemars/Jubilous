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
