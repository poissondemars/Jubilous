from __future__ import annotations

import re
from datetime import date


_DATE_RE = re.compile(r"^(\d{1,2})-(\d{1,2})(?:-(\d{4}))?$")


def parse_birthday_date(text: str) -> tuple[int, int, int | None]:
    """Parses 'DD-MM' or 'DD-MM-YYYY' into (month, day, year|None).

    Raises ValueError if the text doesn't match the expected format or
    doesn't represent a real calendar date.
    """
    match = _DATE_RE.match(text.strip())
    if not match:
        raise ValueError(f"Invalid date format: {text!r}. Use DD-MM or DD-MM-YYYY.")

    day_str, month_str, year_str = match.groups()
    day = int(day_str)
    month = int(month_str)
    year = int(year_str) if year_str else None

    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month: {month}")
    if not (1 <= day <= 31):
        raise ValueError(f"Invalid day: {day}")

    # Validate the date actually exists. Use a leap year when no year is
    # given so that Feb 29 (year-less) is accepted.
    check_year = year if year is not None else 2024
    try:
        date(check_year, month, day)
    except ValueError as exc:
        raise ValueError(f"Invalid date: {text!r} ({exc})") from exc

    return month, day, year


def _safe_date(year: int, month: int, day: int) -> date:
    """Builds a date, treating Feb 29 in a non-leap year as Feb 28."""
    if month == 2 and day == 29:
        try:
            return date(year, 2, 29)
        except ValueError:
            return date(year, 2, 28)
    return date(year, month, day)


def days_until(today: date, month: int, day: int) -> int:
    """Returns the number of days from `today` until the next occurrence
    of the given month/day (0 if it's today, otherwise 1-365)."""
    candidate = _safe_date(today.year, month, day)
    if candidate < today:
        candidate = _safe_date(today.year + 1, month, day)
    return (candidate - today).days


def age_on_next_birthday(year: int | None, month: int, day: int, today: date) -> int | None:
    """Returns the age the person turns on their next occurrence of
    month/day, or None if `year` (birth year) is unknown."""
    if year is None:
        return None

    candidate = _safe_date(today.year, month, day)
    next_age = today.year - year
    if candidate < today:
        next_age += 1
    return next_age
