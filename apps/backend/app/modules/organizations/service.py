"""Organizations service: platform org creation/soft-delete + tenant-scoped CRUD.

Tenant scoping matches the users module: the tenant id always comes from the resolved
``AuthContext``, never from request input (reunionai-multitenant-security). Organization
soft-delete cascades to its properties and memberships; property soft-delete clears
memberships' ``property_id`` (api-contract §4.7). All rows are preserved.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.audit.models import AuditEvent
from app.modules.organizations.models import Membership, Organization, Property
from app.modules.organizations.schemas import (
    MembershipCreateRequest,
    MembershipResponse,
    MembershipUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    PropertyCreateRequest,
    PropertyResponse,
    PropertyUpdateRequest,
)
from app.modules.users.models import User


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


def _to_property(prop: Property) -> PropertyResponse:
    return PropertyResponse(
        id=prop.id,
        organization_id=prop.organization_id,
        name=prop.name,
        code=prop.code,
        description=prop.description,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
    )


def _to_membership(
    membership: Membership, email: str | None, full_name: str | None
) -> MembershipResponse:
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        property_id=membership.property_id,
        role=membership.role,
        is_active=membership.is_active,
        user_email=email,
        user_full_name=full_name,
        created_at=membership.created_at,
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

    # -- tenant-scoped org read/update ----------------------------------------

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

    # -- properties -----------------------------------------------------------

    async def list_properties(
        self, session: AsyncSession, tenant_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[PropertyResponse], int]:
        stmt = (
            select(Property)
            .where(Property.organization_id == tenant_id, Property.deleted_at.is_(None))
            .order_by(Property.created_at.desc())
        )
        rows = (await session.execute(stmt)).scalars().all()
        total = len(rows)
        start = (page - 1) * page_size
        return [_to_property(p) for p in rows[start : start + page_size]], total

    async def create_property(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        payload: PropertyCreateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> PropertyResponse:
        await self._ensure_code_free(session, tenant_id, payload.code)
        prop = Property(
            organization_id=tenant_id,
            name=payload.name,
            code=payload.code,
            description=payload.description,
        )
        session.add(prop)
        await session.flush()
        self._record_audit(
            session, actor, tenant_id, "property.create", "property", prop.id, ip, user_agent
        )
        await session.commit()
        return _to_property(prop)

    async def update_property(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        property_id: uuid.UUID,
        payload: PropertyUpdateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> PropertyResponse:
        prop = await self._get_property(session, tenant_id, property_id)
        fields = payload.model_fields_set
        if "code" in fields and payload.code is not None:
            await self._ensure_code_free(session, tenant_id, payload.code, exclude_id=prop.id)
        if "name" in fields and payload.name is not None:
            prop.name = payload.name
        if "code" in fields:
            prop.code = payload.code
        if "description" in fields:
            prop.description = payload.description
        prop.updated_at = datetime.now(UTC)
        self._record_audit(
            session, actor, tenant_id, "property.update", "property", prop.id, ip, user_agent
        )
        await session.commit()
        return _to_property(prop)

    async def soft_delete_property(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        property_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        prop = await self._get_property(session, tenant_id, property_id)
        prop.deleted_at = datetime.now(UTC)
        prop.updated_at = prop.deleted_at
        await session.execute(
            update(Membership)
            .where(Membership.property_id == property_id, Membership.deleted_at.is_(None))
            .values(property_id=None)
        )
        self._record_audit(
            session, actor, tenant_id, "property.delete", "property", prop.id, ip, user_agent
        )
        await session.commit()

    # -- memberships ----------------------------------------------------------

    async def list_memberships(
        self, session: AsyncSession, tenant_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[MembershipResponse], int]:
        stmt = (
            select(Membership, User.email, User.full_name)
            .join(User, Membership.user_id == User.id)
            .where(Membership.organization_id == tenant_id, Membership.deleted_at.is_(None))
            .order_by(Membership.created_at.desc())
        )
        rows = (await session.execute(stmt)).all()
        total = len(rows)
        start = (page - 1) * page_size
        return [self._row_to_membership(row) for row in rows[start : start + page_size]], total

    async def create_membership(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        payload: MembershipCreateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> MembershipResponse:
        user = await session.get(User, payload.user_id)
        if user is None or user.deleted_at is not None:
            raise APIError(404, "USER_NOT_FOUND", "User not found")
        if payload.property_id is not None:
            await self._get_property(session, tenant_id, payload.property_id)
        existing = (
            await session.execute(
                select(Membership.id).where(
                    Membership.user_id == payload.user_id,
                    Membership.organization_id == tenant_id,
                    Membership.deleted_at.is_(None),
                )
            )
        ).first()
        if existing is not None:
            raise APIError(
                409, "MEMBERSHIP_EXISTS", "User is already a member of this organization"
            )
        membership = Membership(
            user_id=payload.user_id,
            organization_id=tenant_id,
            property_id=payload.property_id,
            role=payload.role,
        )
        session.add(membership)
        await session.flush()
        self._record_audit(
            session,
            actor,
            tenant_id,
            "membership.create",
            "membership",
            membership.id,
            ip,
            user_agent,
        )
        await session.commit()
        return _to_membership(membership, user.email, user.full_name)

    async def update_membership(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        membership_id: uuid.UUID,
        payload: MembershipUpdateRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> MembershipResponse:
        row = await self._get_membership_row(session, tenant_id, membership_id)
        membership = row[0]
        fields = payload.model_fields_set
        if "role" in fields and payload.role is not None:
            membership.role = payload.role
        if "property_id" in fields:
            if payload.property_id is not None:
                await self._get_property(session, tenant_id, payload.property_id)
            membership.property_id = payload.property_id
        membership.updated_at = datetime.now(UTC)
        self._record_audit(
            session,
            actor,
            tenant_id,
            "membership.update",
            "membership",
            membership.id,
            ip,
            user_agent,
        )
        await session.commit()
        return self._row_to_membership(row)

    async def soft_delete_membership(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: uuid.UUID,
        membership_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        row = await self._get_membership_row(session, tenant_id, membership_id)
        membership = row[0]
        if membership.user_id == actor:
            raise APIError(403, "REMOVE_NOT_ALLOWED", "Cannot remove your own membership")
        if membership.role == "org_admin":
            admins = (
                await session.execute(
                    select(func.count())
                    .select_from(Membership)
                    .where(
                        Membership.organization_id == tenant_id,
                        Membership.role == "org_admin",
                        Membership.deleted_at.is_(None),
                    )
                )
            ).scalar_one()
            if admins <= 1:
                raise APIError(
                    403, "REMOVE_NOT_ALLOWED", "Cannot remove the last organization admin"
                )
        membership.deleted_at = datetime.now(UTC)
        membership.updated_at = membership.deleted_at
        self._record_audit(
            session,
            actor,
            tenant_id,
            "membership.delete",
            "membership",
            membership.id,
            ip,
            user_agent,
        )
        await session.commit()

    # -- helpers --------------------------------------------------------------

    def _row_to_membership(self, row: Any) -> MembershipResponse:
        membership, email, full_name = row[0], row[1], row[2]
        return _to_membership(membership, email, full_name)

    async def _get_org(self, session: AsyncSession, tenant_id: uuid.UUID) -> Organization:
        org = await session.get(Organization, tenant_id)
        if org is None or org.deleted_at is not None:
            raise APIError(404, "ORGANIZATION_NOT_FOUND", "Organization not found")
        return org

    async def _get_property(
        self, session: AsyncSession, tenant_id: uuid.UUID, property_id: uuid.UUID
    ) -> Property:
        prop = await session.get(Property, property_id)
        if prop is None or prop.deleted_at is not None or prop.organization_id != tenant_id:
            raise APIError(404, "PROPERTY_NOT_FOUND", "Property not found in tenant")
        return prop

    async def _get_membership_row(
        self, session: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> Any:
        row = (
            await session.execute(
                select(Membership, User.email, User.full_name)
                .join(User, Membership.user_id == User.id)
                .where(
                    Membership.id == membership_id,
                    Membership.organization_id == tenant_id,
                    Membership.deleted_at.is_(None),
                )
            )
        ).first()
        if row is None:
            raise APIError(404, "MEMBERSHIP_NOT_FOUND", "Membership not found in tenant")
        return row

    async def _ensure_code_free(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        code: str | None,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        if not code:
            return
        stmt = select(Property.id).where(
            Property.organization_id == tenant_id,
            Property.code == code,
            Property.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(Property.id != exclude_id)
        if (await session.execute(stmt)).first() is not None:
            raise APIError(
                409, "PROPERTY_CODE_EXISTS", "Property code already exists in organization"
            )

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
