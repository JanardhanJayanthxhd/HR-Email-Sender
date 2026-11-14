import asyncio

from src.config import Settings
from src.logger import log
from src.storage.db import init_db


def main() -> None:
    settings = Settings()

    from src.bot.handlers import (
        handle_edit_callback,
        handle_email_choice,
        handle_message,
        handle_resume_choice,
        handle_send_callback,
        handle_skip_callback,
        help_command,
        resume_command,
        start_command,
    )

    # Initialize database
    asyncio.run(init_db(settings.database_path))
    log.info(f"Database initialized, path={str(settings.database_path)}")

    # Build application
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        MessageHandler,
        filters,
    )

    app = Application.builder().token(settings.telegram_bot_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("resume", resume_command))

    # Message handler (job posts and edit responses)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_send_callback, pattern="^send_"))
    app.add_handler(CallbackQueryHandler(handle_edit_callback, pattern="^edit_"))
    app.add_handler(CallbackQueryHandler(handle_skip_callback, pattern="^skip_"))
    app.add_handler(CallbackQueryHandler(handle_email_choice, pattern="^email_"))
    app.add_handler(CallbackQueryHandler(handle_resume_choice, pattern="^resume_"))

    log.info("Bot starting", provider=settings.llm_provider, model=settings.llm_model)

    # Run bot
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Bot stopped by user")
    except Exception:
        log.exception("Bot stopped because of an unhandled error")
        raise
