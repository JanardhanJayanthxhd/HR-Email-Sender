from pathlib import Path
from src.bot.keyboards import approval_keyboard, email_choice_keyboard, resume_choice_keyboard


def test_approval_keyboard():
    keyboard = approval_keyboard("draft123")

    assert len(keyboard.inline_keyboard) == 1
    assert len(keyboard.inline_keyboard[0]) == 3
    assert keyboard.inline_keyboard[0][0].text == "✅ Send"
    assert keyboard.inline_keyboard[0][0].callback_data == "send_draft123"


def test_email_choice_keyboard():
    emails = ["hr@test.com", "recruiting@test.com"]
    keyboard = email_choice_keyboard(emails)

    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[0][0].text == "1️⃣ hr@test.com"
    assert keyboard.inline_keyboard[0][0].callback_data == "email_0"


def test_resume_choice_keyboard():
    resumes = [Path("resume1.pdf"), Path("resume2.pdf")]
    keyboard = resume_choice_keyboard(resumes)

    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[0][0].text == "1️⃣ resume1.pdf"
    assert keyboard.inline_keyboard[0][0].callback_data == "resume_0"