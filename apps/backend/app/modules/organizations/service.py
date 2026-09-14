"""Organizations service: platform org creation (super-admin) + tenant-scoped CRUD.

Tenant scoping matches the users module: the tenant id always comes from the resolved
``AuthContext``, never from request input (reunionai-multitenant-security). Organization
soft-delete cascades to its properties and memberships by setting ``deleted_at`` (rows
are preserved; the data-model keeps them behind ``deleted_at IS NULL`` filters).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.audit.models import AuditEvent
from app.modules.organizations.models import Membership, Organization, Property
from app.modules.organizations.schemas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)


def _to_response(org: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        settings=org.settings,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


class OrganizationService:
    # -- platform org creation (super-admin only) -----------------------------

    async def create_organization(
        self,
        session: AsyncSession,
        actor: uuid.UUID,
        payload: OrganizationCreateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> OrganizationResponse:
        existing = (
            await session.execute(
                select(Organization.id).where(
                    Organization.slug == payload.slug,
                    Organization.deleted_at.is_(None),
                )
            )
        ).first()
        if existing is not None:
            raise APIError(409, "SLUG_EXISTS", "Organization slug already exists")
        org = Organization(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            settings=payload.settings,
        )
        session.add(org)
        await session.flush()
        new_id = org.id
        self._record_audit(
            session, actor, new_id, "organization.create", "organization", new_id, ip, user_agent
        )
        await session.commit()
        return _to_response(org)

    # -- tenant-scoped read/update --------------------------------------------

    async def get_me(self, session: AsyncSession, tenant_id: uuid.UUID) -> OrganizationResponse:
        org = await self._get_org(session, tenant_id)
        return _to_response(org)

    async def update_me(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        payload: OrganizationUpdateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> OrganizationResponse:
        org = await self._get_org(session, tenant_id)
        fields = payload.model_fields_set
        if "name" in fields and payload.name is not None:
            org.name = payload.name
        if "description" in fields:
            org.description = payload.description
        if "settings" in fields and payload.settings is not None:
            org.settings = payload.settings
        org.updated_at = datetime.now(UTC)
        self._record_audit(
            session,
            actor,
            tenant_id,
            "organization.update",
            "organization",
            tenant_id,
            ip,
            user_agent,
        )
        await session.commit()
        return _to_response(org)

    # -- platform org soft-delete (super-admin only) --------------------------

    async def soft_delete_organization(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        actor: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> datetime:
        org = await session.get(Organization, organization_id)
        if org is None or org.deleted_at is not None:
            raise APIError(404, "ORGANIZATION_NOT_FOUND", "Organization not found")
        deleted_at = datetime.now(UTC)
        org.deleted_at = deleted_at
        org.updated_at = deleted_at
        # Cascade the soft-delete to properties and memberships: set deleted_at so they
        # drop out of every active scope without a hard DELETE.
        await session.execute(
            update(Property)
            .where(Property.organization_id == organization_id, Property.deleted_at.is_(None))
            .values(deleted_at=deleted_at)
        )
        await session.execute(
            update(Membership)
            .where(
                Membership.organization_id == organization_id,
                Membership.deleted_at.is_(None),
            )
            .values(deleted_at=deleted_at)
        )
        self._record_audit(
            session,
            actor,
            organization_id,
            "organization.delete",
            "organization",
            organization_id,
            ip,
            user_agent,
        )
        await session.commit()
        return deleted_at

    # -- helpers --------------------------------------------------------------

    async def _get_org(self, session: AsyncSession, tenant_id: uuid.UUID) -> Organization:
        org = await session.get(Organization, tenant_id)
        if org is None or org.deleted_at is not None:
            raise APIError(404, "ORGANIZATION_NOT_FOUND", "Organization not found")
        return org

    def _record_audit(
        self,
        session: AsyncSession,
        actor_user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        action: str,
        resource: str,
        resource_id: uuid.UUID | None,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        session.add(
            AuditEvent(
                actor_user_id=actor_user_id,
                tenant_id=tenant_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip=ip,
                user_agent=user_agent,
                metadata_json={},
            )
        )
