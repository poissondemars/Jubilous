from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

import db
from config import BOT_TOKEN, DB_PATH
from handlers import (
    cmd_add,
    cmd_delete,
    cmd_edit,
    cmd_list,
    cmd_settimezone,
    cmd_setwindow,
    cmd_start,
    cmd_upcoming,
)
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)


async def post_init(application: Application) -> None:
    """Starts the reminder scheduler once the bot's event loop is running."""
    setup_scheduler(application, application.bot_data["conn"])


def main() -> None:
    conn = db.connect(DB_PATH)

    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.bot_data["conn"] = conn

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("add", cmd_add))
    application.add_handler(CommandHandler("list", cmd_list))
    application.add_handler(CommandHandler("delete", cmd_delete))
    application.add_handler(CommandHandler("edit", cmd_edit))
    application.add_handler(CommandHandler("upcoming", cmd_upcoming))
    application.add_handler(CommandHandler("settimezone", cmd_settimezone))
    application.add_handler(CommandHandler("setwindow", cmd_setwindow))

    application.run_polling()


if __name__ == "__main__":
    main()
