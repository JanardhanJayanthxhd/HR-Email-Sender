from pathlib import Path

from src.bot.keyboards import (
    approval_keyboard,
    edit_choice_keyboard,
    email_choice_keyboard,
    email_template_keyboard,
    resume_choice_keyboard,
)
from src.mailer.email_templates import EMAIL_TEMPLATES


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


def test_email_template_keyboard_is_numbered_for_each_template():
    keyboard = email_template_keyboard()

    assert len(keyboard.inline_keyboard) == len(EMAIL_TEMPLATES)
    assert [
        row[0].callback_data for row in keyboard.inline_keyboard
    ] == [f"template_{number}" for number in range(1, len(EMAIL_TEMPLATES) + 1)]


def test_edit_choice_keyboard():
    keyboard = edit_choice_keyboard("draft123")

    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[0][0].text == "📝 Edit Subject"
    assert keyboard.inline_keyboard[0][0].callback_data == "edit_subject_draft123"
    assert keyboard.inline_keyboard[0][1].text == "✏️ Edit Body"
    assert keyboard.inline_keyboard[0][1].callback_data == "edit_body_draft123"
    assert keyboard.inline_keyboard[1][0].text == "⬅️ Back"
    assert keyboard.inline_keyboard[1][0].callback_data == "edit_back_draft123"
