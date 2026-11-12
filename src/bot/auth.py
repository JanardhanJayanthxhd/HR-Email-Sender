from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from src.config import Settings


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
            if update.effective_user.id != settings.allowed_user_id:
                await update.message.reply_text("⛔ Unauthorized.")
                return None
            return await handler(update, context)
        return wrapper
    return decorator