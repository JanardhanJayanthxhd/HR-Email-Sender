"""Gmail SMTP configuration module."""

from typing import Any


class GmailProvider:
    """Gmail SMTP configuration."""

    def get_smtp_config(self) -> dict[str, Any]:
        """Get Gmail SMTP configuration.

        Returns:
            Dict with Gmail SMTP server and port.
        """
        return {"smtp_server": "smtp.gmail.com", "smtp_port": 587}
