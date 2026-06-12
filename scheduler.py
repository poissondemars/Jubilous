from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import Application

import db
from reminders import build_digest_message, should_send_reminder


async def run_daily_check(conn, bot: Bot, now_utc: datetime | None = None) -> None:
    """Checks every user; sends a digest if it's their reminder time and
    they haven't been sent one today. Always updates last_sent_date for
    users whose reminder time has arrived, even if there's nothing to send,
    so we don't re-check them again for the rest of their local day."""
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    for user in db.get_all_users(conn):
        if not should_send_reminder(now_utc, user.timezone, user.reminder_hour, user.last_sent_date):
            continue

        local_today = now_utc.astimezone(ZoneInfo(user.timezone)).date()
        birthdays = db.get_user_birthdays(conn, user.user_id)
        text = build_digest_message(birthdays, local_today, user.lookahead_days)

        if text is not None:
            await bot.send_message(chat_id=user.user_id, text=text)

        db.update_last_sent_date(conn, user.user_id, local_today.isoformat())


def setup_scheduler(application: Application, conn) -> AsyncIOScheduler:
    """Creates and starts an hourly job that runs run_daily_check.
    Must be called from within a running asyncio event loop (e.g. from a
    PTB post_init hook)."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_check, "interval", hours=1, args=[conn, application.bot])
    scheduler.start()
    return scheduler
