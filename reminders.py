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


def build_digest_message(birthdays: list[Birthday], today: date, window_days: int) -> str | None:
    """Returns a formatted digest of today's and upcoming birthdays, or
    None if there is nothing to report within window_days."""
    today_entries: list[str] = []
    upcoming_entries: list[tuple[int, str]] = []

    for b in birthdays:
        delta = days_until(today, b.month, b.day)

        if delta == 0:
            age = age_on_next_birthday(b.year, b.month, b.day, today)
            label = b.name if age is None else f"{b.name} (turns {age})"
            today_entries.append(label)
        elif delta <= window_days:
            date_str = f"{b.day:02d}-{b.month:02d}"
            plural = "s" if delta != 1 else ""
            upcoming_entries.append((delta, f"{b.name} — in {delta} day{plural} ({date_str})"))

    if not today_entries and not upcoming_entries:
        return None

    lines: list[str] = []

    if today_entries:
        lines.append("🎂 Today's birthdays:")
        for entry in today_entries:
            lines.append(f"  • {entry}")

    if upcoming_entries:
        if lines:
            lines.append("")
        upcoming_entries.sort(key=lambda item: item[0])
        lines.append(f"📅 Coming up (next {window_days} days):")
        for _, entry in upcoming_entries:
            lines.append(f"  • {entry}")

    return "\n".join(lines)
