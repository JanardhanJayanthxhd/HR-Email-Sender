from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers import (
    _get_selected_resume,
    handle_message,
    handle_send_callback,
    handle_template_choice,
    start_command,
)
from src.mailer.email_templates import EMAIL_TEMPLATES
from src.models import JobPost


def test_get_selected_resume_recovers_single_resume(tmp_path, monkeypatch):
    resume_dir = tmp_path / "resume"
    resume_dir.mkdir()
    resume_path = resume_dir / "resume.pdf"
    resume_path.write_bytes(b"fake")
    monkeypatch.setattr("src.bot.handlers.settings.resume_dir", resume_dir)

    context = MagicMock()
    context.user_data = {}

    assert _get_selected_resume(context) == resume_path
    assert context.user_data["selected_resume"] == resume_path


@pytest.mark.asyncio
async def test_start_command_single_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "123")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")

    # Create single resume
    resume_dir = tmp_path / "resume"
    resume_dir.mkdir()
    (resume_dir / "resume.pdf").write_bytes(b"fake")

    with patch("src.bot.handlers.settings.resume_dir", resume_dir), \
         patch("src.bot.handlers.settings.allowed_user_id", 123):
        mock_update = MagicMock()
        mock_update.effective_user.id = 123
        mock_update.message.reply_text = AsyncMock()
        mock_update.effective_message = mock_update.message
        mock_context = MagicMock()

        await start_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        assert "resume.pdf" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_send_callback_enforces_daily_cap(tmp_path, monkeypatch):
    """Review Focus #3: Daily cap enforcement."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "123")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")
    monkeypatch.setenv("DAILY_SEND_CAP", "2")

    db_path = tmp_path / "test.db"

    with patch("src.bot.handlers.settings.database_path", db_path), \
         patch("src.bot.handlers.settings.allowed_user_id", 123), \
         patch("src.bot.handlers.settings.daily_send_cap", 2), \
         patch("src.bot.handlers.get_daily_send_count", return_value=2):  # At cap

        mock_update = MagicMock()
        mock_update.effective_user.id = 123
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.message.reply_text = AsyncMock()
        mock_update.effective_message = mock_update.callback_query.message
        mock_update.callback_query.data = "send_draft_id"
        mock_context = MagicMock()
        mock_context.user_data = {"draft_id": {"subject": "Test"}}

        await handle_send_callback(mock_update, mock_context)

        # Should show cap error, not send
        call_args = mock_update.callback_query.message.reply_text.call_args[0][0]
        assert "Daily send limit reached" in call_args


@pytest.mark.asyncio
async def test_handle_template_choice_renders_selected_template(monkeypatch):
    with (
        patch("src.bot.handlers.settings.allowed_user_id", 123),
        patch("src.bot.handlers.settings.sender_name", "Configured Name"),
        patch("src.bot.handlers.settings.sender_phone", "+1 555 010 1234"),
    ):
        mock_update = MagicMock()
        mock_update.effective_user.id = 123
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.data = "template_2"
        mock_update.callback_query.message.reply_text = AsyncMock()
        mock_update.effective_message = mock_update.callback_query.message
        mock_context = MagicMock()
        mock_context.user_data = {
            "pending_application": {
                "job_post": JobPost(
                    company="Acme",
                    role="Frontend Developer",
                    hr_emails=["hr@acme.com"],
                ),
            }
        }

        await handle_template_choice(mock_update, mock_context)

        mock_update.callback_query.answer.assert_awaited_once()
        mock_update.callback_query.message.reply_text.assert_awaited_once()
        message = mock_update.callback_query.message.reply_text.call_args.args[0]
        assert "2. Straightforward" in message
        assert "Frontend Developer" in message
        assert "Configured Name\n+1 555 010 1234" in message
        assert "pending_application" not in mock_context.user_data


@pytest.mark.asyncio
async def test_handle_message_prompts_for_template_without_profile():
    job_text = "Acme is hiring a developer. Contact: hr@acme.com."
    job_post = JobPost(
        company="Acme",
        role="Python Developer",
        hr_emails=["hr@acme.com"],
    )
    mock_llm = object()

    with patch("src.bot.handlers.settings.allowed_user_id", 123), \
         patch("src.bot.handlers.get_llm", return_value=mock_llm), \
         patch("src.bot.handlers.init_db", new_callable=AsyncMock), \
         patch(
             "src.bot.handlers.get_applications_by_hr_email",
             new_callable=AsyncMock,
             return_value=[("Acme", "Backend Developer", "2026-11-17 10:30:00")],
         ), \
         patch(
             "src.bot.handlers.extract_job_post",
             new_callable=AsyncMock,
             return_value=job_post,
         ) as mock_extract:
        mock_update = MagicMock()
        mock_update.effective_user.id = 123
        mock_update.message.text = job_text
        mock_update.message.reply_text = AsyncMock()
        mock_update.effective_message = mock_update.message
        mock_context = MagicMock()
        mock_context.user_data = {}

        await handle_message(mock_update, mock_context)

        mock_extract.assert_awaited_once_with(job_text, mock_llm)
        response = mock_update.message.reply_text.call_args_list[-1].args[0]
        assert "Extracted job details:" in response
        assert "company name: Acme" in response
        assert "hr email(s): hr@acme.com" in response
        assert "role: Python Developer" in response
        assert "Previously sent applications to these HR emails:" in response
        assert "Backend Developer at Acme — 2026-11-17 10:30:00 UTC" in response
        assert f"Choose an email template (1-{len(EMAIL_TEMPLATES)}):" in response
        assert mock_context.user_data["pending_application"] == {"job_post": job_post}
        keyboard = mock_update.message.reply_text.call_args_list[-1].kwargs["reply_markup"]
        assert keyboard.inline_keyboard[0][0].callback_data == "template_1"


@pytest.mark.asyncio
async def test_handle_message_continues_when_application_history_lookup_fails():
    job_text = "Acme is hiring a developer. Contact: hr@acme.com."
    job_post = JobPost(
        company="Acme",
        role="Python Developer",
        hr_emails=["hr@acme.com"],
    )

    with (
        patch("src.bot.handlers.settings.allowed_user_id", 123),
        patch("src.bot.handlers.get_llm", return_value=object()),
        patch("src.bot.handlers.init_db", new_callable=AsyncMock),
        patch(
            "src.bot.handlers.get_applications_by_hr_email",
            new_callable=AsyncMock,
            side_effect=OSError("database unavailable"),
        ),
        patch(
            "src.bot.handlers.extract_job_post",
            new_callable=AsyncMock,
            return_value=job_post,
        ),
    ):
        mock_update = MagicMock()
        mock_update.effective_user.id = 123
        mock_update.message.text = job_text
        mock_update.message.reply_text = AsyncMock()
        mock_update.effective_message = mock_update.message
        mock_context = MagicMock()
        mock_context.user_data = {}

        await handle_message(mock_update, mock_context)

        response = mock_update.message.reply_text.call_args_list[-1].args[0]
        assert "Could not check previous applications" in response
        assert "Choose an email template" in response
        assert mock_context.user_data["pending_application"] == {"job_post": job_post}
