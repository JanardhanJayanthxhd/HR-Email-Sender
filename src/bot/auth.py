from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from src.config import Settings
from src.logger import log


def authorized_only(settings: Settings):
    """Decorator to restrict handler to authorized user only.

    Args:
        settings: Application settings with allowed_user_id.

    Returns:
        Decorator function.
    """

    def decorator(handler):
        @wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            if user is None or user.id != settings.allowed_user_id:
                log.warning("Rejected unauthorized Telegram update")
                message = update.effective_message
                if message is not None:
                    await message.reply_text("⛔ Unauthorized.")
                return None
            return await handler(update, context)

        return wrapper

    return decorator
