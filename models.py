from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    user_id: int
    timezone: str
    lookahead_days: int
    reminder_hour: int
    last_sent_date: str | None


@dataclass
class Birthday:
    id: int
    user_id: int
    name: str
    month: int
    day: int
    year: int | None
    notes: str | None
