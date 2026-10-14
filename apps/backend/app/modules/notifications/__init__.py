"""Notifications module (email notifications for state changes)."""

from app.modules.notifications.providers import (
    EmailMessage,
    EmailProvider,
    MockNotificationProvider,
    NotificationProvider,
)
from app.modules.notifications.router import router as notifications_router
from app.modules.notifications.service import NotificationsService

__all__ = [
    "EmailMessage",
    "EmailProvider",
    "MockNotificationProvider",
    "NotificationProvider",
    "NotificationsService",
    "notifications_router",
]
