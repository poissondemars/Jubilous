from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

import db
from birthdays import parse_birthday_date


WELCOME_TEXT = (
    "👋 Welcome to the Birthday Reminder bot!\n\n"
    "Commands:\n"
    "/add <Name> <DD-MM[-YYYY]> [notes] — add a birthday\n"
    "/list — list all your birthdays\n"
    "/upcoming [days] — show upcoming birthdays\n"
    "/edit <id> <Name> <DD-MM[-YYYY]> [notes] — edit a birthday\n"
    "/delete <id> — delete a birthday\n"
    "/settimezone <IANA tz name> — set your timezone (e.g. Europe/Berlin)\n"
    "/setwindow <days> — set the lookahead window for reminders"
)

ADD_USAGE = "Usage: /add <Name> <DD-MM[-YYYY]> [notes]\nExample: /add Mom 14-03-1965 loves flowers"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    db.get_or_create_user(conn, update.effective_user.id)
    await update.message.reply_text(WELCOME_TEXT)


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id
    db.get_or_create_user(conn, user_id)

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(ADD_USAGE)
        return

    name = args[0]
    try:
        month, day, year = parse_birthday_date(args[1])
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
        return

    notes = " ".join(args[2:]) if len(args) > 2 else None
    birthday_id = db.add_birthday(conn, user_id, name, month, day, year, notes)

    date_str = f"{day:02d}-{month:02d}" + (f"-{year}" if year else "")
    await update.message.reply_text(f'✅ Added "{name}" ({date_str}) — id #{birthday_id}')
