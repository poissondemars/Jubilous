from __future__ import annotations

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import db
from birthdays import age_on_next_birthday, days_until, parse_birthday_date


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


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id
    db.get_or_create_user(conn, user_id)

    birthdays = db.get_user_birthdays(conn, user_id)
    if not birthdays:
        await update.message.reply_text("You haven't added any birthdays yet. Use /add to get started.")
        return

    today = date.today()
    birthdays.sort(key=lambda b: days_until(today, b.month, b.day))

    lines = []
    for b in birthdays:
        date_str = f"{b.day:02d}-{b.month:02d}" + (f"-{b.year}" if b.year else "")
        age = age_on_next_birthday(b.year, b.month, b.day, today)

        line = f"#{b.id} {b.name} — {date_str}"
        if age is not None:
            line += f" (turns {age})"
        if b.notes:
            line += f" — {b.notes}"
        lines.append(line)

    await update.message.reply_text("\n".join(lines))


DELETE_USAGE = "Usage: /delete <id>"
EDIT_USAGE = "Usage: /edit <id> <Name> <DD-MM[-YYYY]> [notes]\nExample: /edit 1 Mom 14-03-1965 loves flowers"


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id

    args = context.args
    if len(args) != 1:
        await update.message.reply_text(DELETE_USAGE)
        return

    try:
        birthday_id = int(args[0])
    except ValueError:
        await update.message.reply_text(f"{DELETE_USAGE} (id must be a number)")
        return

    if db.delete_birthday(conn, birthday_id, user_id):
        await update.message.reply_text(f"🗑️ Deleted birthday #{birthday_id}")
    else:
        await update.message.reply_text(f"Birthday #{birthday_id} not found.")


async def cmd_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(EDIT_USAGE)
        return

    try:
        birthday_id = int(args[0])
    except ValueError:
        await update.message.reply_text(f"The id must be a number.\n{EDIT_USAGE}")
        return

    name = args[1]
    try:
        month, day, year = parse_birthday_date(args[2])
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
        return

    notes = " ".join(args[3:]) if len(args) > 3 else None

    if db.update_birthday(conn, birthday_id, user_id, name, month, day, year, notes):
        date_str = f"{day:02d}-{month:02d}" + (f"-{year}" if year else "")
        await update.message.reply_text(f'✅ Updated #{birthday_id}: "{name}" ({date_str})')
    else:
        await update.message.reply_text(f"Birthday #{birthday_id} not found.")


UPCOMING_USAGE = "Usage: /upcoming [days] (days must be a positive number)"


async def cmd_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = context.bot_data["conn"]
    user_id = update.effective_user.id
    user = db.get_or_create_user(conn, user_id)

    args = context.args
    if args:
        try:
            window_days = int(args[0])
            if window_days < 1:
                raise ValueError
        except ValueError:
            await update.message.reply_text(UPCOMING_USAGE)
            return
    else:
        window_days = user.lookahead_days

    today = date.today()
    birthdays = db.get_user_birthdays(conn, user_id)

    entries: list[tuple[int, str]] = []
    for b in birthdays:
        delta = days_until(today, b.month, b.day)
        if delta > window_days:
            continue

        date_str = f"{b.day:02d}-{b.month:02d}"
        if delta == 0:
            entries.append((delta, f"{b.name} — today ({date_str})"))
        else:
            plural = "s" if delta != 1 else ""
            entries.append((delta, f"{b.name} — in {delta} day{plural} ({date_str})"))

    if not entries:
        await update.message.reply_text(f"No birthdays in the next {window_days} days.")
        return

    entries.sort(key=lambda item: item[0])
    lines = [f"🎂 Birthdays in the next {window_days} days:"]
    for _, entry in entries:
        lines.append(f"  • {entry}")

    await update.message.reply_text("\n".join(lines))
