"""Email sending functionality using SMTP."""

import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from email_config import GmailProvider


class EmailSender:
    """Handle email sending operations."""

    def __init__(self, email: str, password: str, sender_name: str):
        """Initialize email sender with Gmail credentials.

        Args:
            email: Sender Gmail address.
            password: Gmail app password.
            sender_name: Sender's full name.
        """
        self.email = email
        self.password = password
        self.sender_name = sender_name

        provider = GmailProvider()
        config = provider.get_smtp_config()
        self.smtp_server = config["smtp_server"]
        self.smtp_port = config["smtp_port"]

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        attachment_path: str | None = None,
    ) -> bool:
        """Send email with optional attachment.

        Args:
            recipient_email: Recipient's email address.
            subject: Email subject line.
            body: Email body content.
            attachment_path: Path to attachment file (optional).

        Returns:
            True if email sent successfully, False otherwise.
        """
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self.sender_name} <{self.email}>"
            msg["To"] = recipient_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, "rb") as f:
                    attachment = MIMEApplication(f.read(), _subtype="pdf")
                    attachment.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=Path(attachment_path).name,
                    )
                    msg.attach(attachment)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Error sending email: {e!s}")
            return False
