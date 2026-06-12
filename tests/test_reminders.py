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
