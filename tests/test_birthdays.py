from datetime import date

import pytest

from birthdays import age_on_next_birthday, days_until, parse_birthday_date


def test_parse_date_without_year():
    assert parse_birthday_date("14-03") == (3, 14, None)


def test_parse_date_with_year():
    assert parse_birthday_date("14-03-1965") == (3, 14, 1965)


def test_parse_date_invalid_format_raises():
    with pytest.raises(ValueError):
        parse_birthday_date("not-a-date")


def test_parse_date_invalid_month_raises():
    with pytest.raises(ValueError):
        parse_birthday_date("01-13")


def test_parse_date_invalid_day_raises():
    with pytest.raises(ValueError):
        parse_birthday_date("32-01")


def test_parse_date_feb29_without_year_is_valid():
    assert parse_birthday_date("29-02") == (2, 29, None)


def test_days_until_today_is_zero():
    today = date(2026, 6, 11)
    assert days_until(today, 6, 11) == 0


def test_days_until_later_this_year():
    today = date(2026, 6, 11)
    assert days_until(today, 6, 20) == 9


def test_days_until_wraps_to_next_year():
    today = date(2026, 6, 11)
    assert days_until(today, 1, 1) == 204


def test_days_until_feb29_in_non_leap_year_treated_as_feb28():
    today = date(2025, 2, 27)  # 2025 is not a leap year
    assert days_until(today, 2, 29) == 1


def test_age_on_next_birthday_before_birthday_this_year():
    today = date(2026, 6, 11)
    assert age_on_next_birthday(1990, 6, 20, today) == 36


def test_age_on_next_birthday_after_birthday_this_year():
    today = date(2026, 6, 11)
    assert age_on_next_birthday(1990, 1, 1, today) == 37


def test_age_on_next_birthday_today_is_birthday():
    today = date(2026, 6, 11)
    assert age_on_next_birthday(1990, 6, 11, today) == 36


def test_age_on_next_birthday_unknown_year_returns_none():
    today = date(2026, 6, 11)
    assert age_on_next_birthday(None, 6, 20, today) is None
