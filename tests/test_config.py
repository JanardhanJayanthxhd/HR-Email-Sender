# tests/test_config.py

from src.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLOWED_USER_ID", raising=False)
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    monkeypatch.delenv("REPLY_TO_EMAIL", raising=False)
    monkeypatch.delenv("SENDER_NAME", raising=False)

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("ALLOWED_USER_ID", "12345")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test_pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test User")

    settings = Settings(_env_file=None)

    assert settings.telegram_bot_token == "test_token"
    assert settings.allowed_user_id == 12345
    assert settings.llm_provider == "ollama"  # default
    assert settings.daily_send_cap == 15  # default


def test_settings_validates_required_fields(monkeypatch):
    import pytest
    from pydantic import ValidationError

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLOWED_USER_ID", raising=False)
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    monkeypatch.delenv("REPLY_TO_EMAIL", raising=False)
    monkeypatch.delenv("SENDER_NAME", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # Missing required fields
