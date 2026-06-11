import pytest

from birthdays import parse_birthday_date


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
