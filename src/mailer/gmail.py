from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import aiosmtplib


async def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_path: Path,
    sender_email: str,
    sender_password: str,
    sender_name: str,
    reply_to: str
) -> bool:
    """Send email via Gmail SMTP with attachment.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body content.
        attachment_path: Path to PDF resume file.
        sender_email: Gmail address.
        sender_password: Gmail app password.
        sender_name: Sender's full name.
        reply_to: Reply-To email address.

    Returns:
        True if sent successfully, False otherwise.
    """
    try:
        # Check if attachment exists (Review Focus #4)
        if not attachment_path.exists():
            return False

        # Build message
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body, "plain"))

        # Attach resume
        with open(attachment_path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=attachment_path.name
            )
            msg.attach(attachment)

        # Send via Gmail SMTP (SSL port 465)
        async with aiosmtplib.SMTP(hostname="smtp.gmail.com", port=465, ssl=True) as smtp:
            await smtp.login(sender_email, sender_password)
            await smtp.send_message(msg)

        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False