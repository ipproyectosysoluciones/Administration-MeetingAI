"""Notifications service: email notifications for state changes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.audit.models import AuditEvent
from app.modules.notifications.providers import EmailMessage, EmailProvider, MockNotificationProvider, NotificationProvider
from app.modules.users.models import User


class NotificationsService:
    def __init__(self, provider: Optional[NotificationProvider] = None) -> None:
        self._provider = provider or MockNotificationProvider()

    async def send_notification(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        recipient_user_ids: list[uuid.UUID],
        subject: str,
        body: str,
        body_html: str | None = None,
        action: str = "notification",
        resource_id: uuid.UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> int:
        """Send email notifications to multiple users."""
        # Fetch recipients
        if not recipient_user_ids:
            return 0

        users = (await session.execute(
            select(User).where(User.id.in_(recipient_user_ids))
        )).scalars().all()

        if not users:
            return 0

        sent_count = 0
        for user in users:
            if not user.is_active or user.deleted_at:
                continue

            message = EmailMessage(
                to=[user.email],
                subject=subject,
                body=body,
                body_html=body_html,
            )

            try:
                success = await self._provider.send_email(message)
                if success:
                    sent_count += 1
                    # Audit log
                    await self._audit(
                        session,
                        tenant_id=tenant_id,
                        actor=recipient_user_ids[0],  # system action
                        action=f"notification.{action}",
                        resource="notification",
                        resource_id=resource_id,
                        ip=ip,
                        user_agent=user_agent,
                    )
            except Exception as e:
                # Log but don't fail the whole batch
                print(f"Failed to send notification to {user.email}: {e}")

        return sent_count

    async def notify_minute_reviewed(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        minute_id: uuid.UUID,
        minute_title: str,
        reviewed_by: uuid.UUID,
        reviewer_name: str,
        recipient_user_ids: list[uuid.UUID],
    ) -> int:
        """Notify when a minute is reviewed."""
        return await self.send_notification(
            session,
            tenant_id=tenant_id,
            recipient_user_ids=recipient_user_ids,
            subject=f"Acta revisada: {minute_title}",
            body=(
                f"La acta '{minute_title}' ha sido revisada por {reviewer_name}.\n\n"
                f"Estado actual: En revisión\n\n"
                f"Puedes consultar los cambios en la plataforma."
            ),
            action="minute.reviewed",
            resource_id=minute_id,
        )

    async def notify_minute_approved(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        minute_id: uuid.UUID,
        minute_title: str,
        approved_by: uuid.UUID,
        approver_name: str,
        recipient_user_ids: list[uuid.UUID],
    ) -> int:
        """Notify when a minute is approved."""
        return await self.send_notification(
            session,
            tenant_id=tenant_id,
            recipient_user_ids=recipient_user_ids,
            subject=f"Acta aprobada: {minute_title}",
            body=(
                f"La acta '{minute_title}' ha sido aprobada por {approver_name}.\n\n"
                f"La acta ya está lista para publicación.\n\n"
                f"Puedes consultar la acta en la plataforma."
            ),
            action="minute.approved",
            resource_id=minute_id,
        )

    async def notify_minute_published(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        minute_id: uuid.UUID,
        minute_title: str,
        published_by: uuid.UUID,
        publisher_name: str,
        recipient_user_ids: list[uuid.UUID],
    ) -> int:
        """Notify when a minute is published."""
        return await self.send_notification(
            session,
            tenant_id=tenant_id,
            recipient_user_ids=recipient_user_ids,
            subject=f"Acta publicada: {minute_title}",
            body=(
                f"La acta '{minute_title}' ha sido publicada por {publisher_name}.\n\n"
                f"La acta ya está disponible para consulta por los miembros autorizados.\n\n"
                f"Puedes consultar la acta en la plataforma."
            ),
            action="minute.published",
            resource_id=minute_id,
        )

    async def notify_minute_archived(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        minute_id: uuid.UUID,
        minute_title: str,
        archived_by: uuid.UUID,
        archiver_name: str,
        recipient_user_ids: list[uuid.UUID],
    ) -> int:
        """Notify when a minute is archived."""
        return await self.send_notification(
            session,
            tenant_id=tenant_id,
            recipient_user_ids=recipient_user_ids,
            subject=f"Acta archivada: {minute_title}",
            body=(
                f"La acta '{minute_title}' ha sido archivada por {archiver_name}.\n\n"
                f"La acta ya no está disponible para edición.\n\n"
                f"Puedes consultar la acta en la plataforma (modo solo lectura)."
            ),
            action="minute.archived",
            resource_id=minute_id,
        )

    async def notify_minute_draft_created(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        minute_id: uuid.UUID,
        minute_title: str,
        created_by: uuid.UUID,
        creator_name: str,
        recipient_user_ids: list[uuid.UUID],
    ) -> int:
        """Notify when a new draft is created."""
        return await self.send_notification(
            session,
            tenant_id=tenant_id,
            recipient_user_ids=recipient_user_ids,
            subject=f"Nuevo borrador de acta: {minute_title}",
            body=(
                f"Se ha creado un nuevo borrador de acta: '{minute_title}' por {creator_name}.\n\n"
                f"Estado: Borrador\n\n"
                f"Puedes revisar y editar el borrador en la plataforma."
            ),
            action="minute.draft.created",
            resource_id=minute_id,
        )

    async def notify_minute_content_updated(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        minute_id: uuid.UUID,
        minute_title: str,
        updated_by: uuid.UUID,
        updater_name: str,
        recipient_user_ids: list[uuid.UUID],
    ) -> int:
        """Notify when minute content is updated (new version)."""
        return await self.send_notification(
            session,
            tenant_id=tenant_id,
            recipient_user_ids=recipient_user_ids,
            subject=f"Acta actualizada: {minute_title}",
            body=(
                f"La acta '{minute_title}' ha sido actualizada por {updater_name}.\n\n"
                f"Se ha creado una nueva versión del borrador.\n\n"
                f"Puedes revisar los cambios en la plataforma."
            ),
            action="minute.content.updated",
            resource_id=minute_id,
        )

    async def _audit(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        action: str,
        resource: str,
        resource_id: uuid.UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        from app.modules.audit.models import AuditEvent
        session.add(
            AuditEvent(
                actor_user_id=actor,
                tenant_id=tenant_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip=ip,
                user_agent=user_agent,
                metadata_json={},
            )
        )