import asyncio
import structlog

from src.config import Settings
from src.bot.handlers import (
    start_command,
    help_command,
    resume_command,
    handle_message,
    handle_send_callback,
    handle_edit_callback,
    handle_skip_callback,
    handle_email_choice,
    handle_resume_choice,
)

from src.storage.db import init_db


logger = structlog.get_logger()


async def main():
    settings = Settings()

    # Initialize database
    await init_db(settings.database_path)
    logger.info("Database initialized", path=str(settings.database_path))

    # Build application
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

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

    logger.info("Bot starting", provider=settings.llm_provider, model=settings.llm_model)

    # Run bot
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")