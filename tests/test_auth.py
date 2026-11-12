import pytest
from unittest.mock import MagicMock, AsyncMock
from src.bot.auth import authorized_only
from src.config import Settings


@pytest.mark.asyncio
async def test_authorized_user_allowed(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "12345")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")

    settings = Settings()

    @authorized_only(settings)
    async def handler(update, context):
        return "success"

    mock_update = MagicMock()
    mock_update.effective_user.id = 12345

    result = await handler(mock_update, None)

    assert result == "success"


@pytest.mark.asyncio
async def test_unauthorized_user_blocked(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "12345")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")

    settings = Settings()

    @authorized_only(settings)
    async def handler(update, context):
        return "success"

    mock_update = MagicMock()
    mock_update.effective_user.id = 99999  # Wrong user ID
    mock_update.message.reply_text = AsyncMock()

    result = await handler(mock_update, None)

    mock_update.message.reply_text.assert_called_once_with("⛔ Unauthorized.")
    assert result is None