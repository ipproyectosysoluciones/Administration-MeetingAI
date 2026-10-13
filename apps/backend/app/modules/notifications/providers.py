"""Notification providers abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    body: str
    body_html: Optional[str] = None
    from_email: Optional[str] = None


class NotificationProvider(ABC):
    """Abstract notification provider."""

    @abstractmethod
    async def send_email(self, message: EmailMessage) -> bool:
        """Send an email notification."""
        ...


class EmailProvider(NotificationProvider):
    """SMTP email provider (placeholder for production SMTP)."""

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    async def send_email(self, message: EmailMessage) -> bool:
        # In production, would use aiosmtplib or similar
        # For now, log the email
        print(f"[EMAIL] To: {message.to}, Subject: {message.subject}")
        print(f"[EMAIL] Body: {message.body[:200]}...")
        return True


class MockNotificationProvider(NotificationProvider):
    """Mock notification provider for testing."""

    def __init__(self) -> None:
        self.sent_messages: list = []

    async def send_email(self, message: EmailMessage) -> bool:
        self.sent_messages.append(message)
        print(f"[MOCK EMAIL] To: {message.to}, Subject: {message.subject}")
        return True