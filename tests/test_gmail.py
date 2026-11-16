from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.mailer.gmail import send_email


@pytest.mark.asyncio
async def test_send_email_success(tmp_path):
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"fake pdf content")

    with patch("src.mailer.gmail.aiosmtplib.SMTP") as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance

        result = await send_email(
            to=["hr@test.com"],
            subject="Test Subject",
            body="Test Body",
            attachment_path=resume_path,
            sender_email="sender@gmail.com",
            sender_password="password",
            sender_name="Test Sender",
            reply_to="reply@gmail.com",
        )

        assert result is True
        mock_smtp.assert_called_once_with(
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
        )
        mock_instance.login.assert_called_once_with("sender@gmail.com", "password")
        mock_instance.send_message.assert_called_once()
        sent_message = mock_instance.send_message.call_args.args[0]
        assert sent_message["To"] == "hr@test.com"
        assert mock_instance.send_message.call_args.kwargs["recipients"] == ["hr@test.com"]


@pytest.mark.asyncio
async def test_send_email_includes_all_recipients_in_to_header(tmp_path):
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"fake pdf content")
    recipients = ["hr@test.com", "careers@test.com"]

    with patch("src.mailer.gmail.aiosmtplib.SMTP") as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance

        result = await send_email(
            to=recipients,
            subject="Test Subject",
            body="Test Body",
            attachment_path=resume_path,
            sender_email="sender@gmail.com",
            sender_password="password",
            sender_name="Test Sender",
            reply_to="reply@gmail.com",
        )

        assert result is True
        sent_message = mock_instance.send_message.call_args.args[0]
        assert sent_message["To"] == "hr@test.com, careers@test.com"
        assert mock_instance.send_message.call_args.kwargs["recipients"] == recipients


@pytest.mark.asyncio
async def test_send_email_missing_attachment():
    """Review Focus #4: Missing resume file."""
    nonexistent = Path("/fake/path/resume.pdf")

    result = await send_email(
        to=["hr@test.com"],
        subject="Test",
        body="Body",
        attachment_path=nonexistent,
        sender_email="sender@gmail.com",
        sender_password="password",
        sender_name="Test",
        reply_to="reply@gmail.com",
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_email_smtp_failure(tmp_path):
    attachment_path = tmp_path / "resume.pdf"
    attachment_path.write_bytes(b"fake pdf content")

    with patch("src.mailer.gmail.aiosmtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("SMTP error")

        result = await send_email(
            to=["hr@test.com"],
            subject="Test",
            body="Body",
            attachment_path=attachment_path,
            sender_email="sender@gmail.com",
            sender_password="password",
            sender_name="Test",
            reply_to="reply@gmail.com",
        )

        assert result is False
