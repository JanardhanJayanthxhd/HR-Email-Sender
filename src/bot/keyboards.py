from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def approval_keyboard(draft_id: str) -> InlineKeyboardMarkup:
    """Build Send / Edit / Skip keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Send", callback_data=f"send_{draft_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{draft_id}"),
            InlineKeyboardButton("⏭️ Skip", callback_data=f"skip_{draft_id}"),
        ]
    ])


def email_choice_keyboard(emails: list[str]) -> InlineKeyboardMarkup:
    """Build numbered email selection keyboard."""
    buttons = [
        [InlineKeyboardButton(f"{i+1}️⃣ {email}", callback_data=f"email_{i}")]
        for i, email in enumerate(emails)
    ]
    return InlineKeyboardMarkup(buttons)


def resume_choice_keyboard(resume_files: list[Path]) -> InlineKeyboardMarkup:
    """Build numbered resume selection keyboard."""
    buttons = [
        [InlineKeyboardButton(f"{i+1}️⃣ {path.name}", callback_data=f"resume_{i}")]
        for i, path in enumerate(resume_files)
    ]
    return InlineKeyboardMarkup(buttons)