import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot.handlers import start_command, handle_send_callback


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

    with patch("src.bot.handlers.settings.resume_dir", resume_dir):
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
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
         patch("src.bot.handlers.get_daily_send_count", return_value=2):  # At cap

        mock_update = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {"draft_id": {}}

        await handle_send_callback(mock_update, mock_context)

        # Should show cap error, not send
        call_args = mock_update.callback_query.message.reply_text.call_args[0][0]
        assert "Daily send limit reached" in call_args