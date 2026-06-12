from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from birthdays import age_on_next_birthday, days_until
from models import Birthday


def should_send_reminder(
    now_utc: datetime,
    timezone: str,
    reminder_hour: int,
    last_sent_date: str | None,
) -> bool:
    """True if the user's current local date differs from last_sent_date
    AND the local hour is >= reminder_hour."""
    local_now = now_utc.astimezone(ZoneInfo(timezone))
    local_date_str = local_now.date().isoformat()

    if local_date_str == last_sent_date:
        return False

    return local_now.hour >= reminder_hour
