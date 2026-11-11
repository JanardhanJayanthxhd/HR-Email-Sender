"""Email provider configuration module.

This module provides SMTP configuration for different email providers
following the Open/Closed Principle for easy extension.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    def get_smtp_config(self) -> dict[str, Any]:
        """Get SMTP configuration for the provider.

        Returns:
            Dict containing smtp_server and smtp_port.
        """
        ...


class GmailProvider(EmailProvider):
    """Gmail SMTP configuration."""

    def get_smtp_config(self) -> dict[str, Any]:
        """Get Gmail SMTP configuration.

        Returns:
            Dict with Gmail SMTP server and port.
        """
        return {"smtp_server": "smtp.gmail.com", "smtp_port": 587}


class OutlookProvider(EmailProvider):
    """Outlook SMTP configuration."""

    def get_smtp_config(self) -> dict[str, Any]:
        """Get Outlook SMTP configuration.

        Returns:
            Dict with Outlook SMTP server and port.
        """
        return {"smtp_server": "smtp-mail.outlook.com", "smtp_port": 587}


class EmailProviderFactory:
    """Factory for creating email provider instances."""

    _providers: ClassVar[dict[str, type[EmailProvider]]] = {
        "gmail": GmailProvider,
        "outlook": OutlookProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> EmailProvider:
        """Get email provider instance by name.

        Args:
            provider_name: Name of the provider ('gmail' or 'outlook').

        Returns:
            EmailProvider instance.

        Raises:
            ValueError: If provider_name is not supported.
        """
        provider_name = provider_name.lower()
        if provider_name not in cls._providers:
            raise ValueError(
                f"Unsupported provider: {provider_name}. "
                f"Supported providers: {', '.join(cls._providers.keys())}"
            )
        return cls._providers[provider_name]()

    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a new email provider.

        Args:
            name: Provider name identifier.
            provider_class: EmailProvider subclass.
        """
        cls._providers[name.lower()] = provider_class
