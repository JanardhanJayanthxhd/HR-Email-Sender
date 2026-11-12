import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from src.mailer.gmail import send_email


@pytest.mark.asyncio
async def test_send_email_success(tmp_path):
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"fake pdf content")

    with patch("src.mailer.gmail.SMTP") as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance

        result = await send_email(
            to="hr@test.com",
            subject="Test Subject",
            body="Test Body",
            attachment_path=resume_path,
            sender_email="sender@gmail.com",
            sender_password="password",
            sender_name="Test Sender",
            reply_to="reply@gmail.com"
        )

        assert result is True
        mock_instance.login.assert_called_once_with("sender@gmail.com", "password")
        mock_instance.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_missing_attachment():
    """Review Focus #4: Missing resume file."""
    nonexistent = Path("/fake/path/resume.pdf")

    result = await send_email(
        to="hr@test.com",
        subject="Test",
        body="Body",
        attachment_path=nonexistent,
        sender_email="sender@gmail.com",
        sender_password="password",
        sender_name="Test",
        reply_to="reply@gmail.com"
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_email_smtp_failure():
    with patch("src.mailer.gmail.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("SMTP error")

        result = await send_email(
            to="hr@test.com",
            subject="Test",
            body="Body",
            attachment_path=Path("resume.pdf"),
            sender_email="sender@gmail.com",
            sender_password="password",
            sender_name="Test",
            reply_to="reply@gmail.com"
        )

        assert result is False