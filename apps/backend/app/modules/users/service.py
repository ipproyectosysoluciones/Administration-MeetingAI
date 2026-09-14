"""Users service: self-service profile and password change (TASK-050, part 1 of 2).

Tenant scoping is enforced by filtering every query on the user's membership in the
caller's organization — the tenant id always comes from the resolved ``AuthContext``,
never from request input (reunionai-multitenant-security). Users are global identities;
they appear in a tenant's listing only via a membership there.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.core.security import PasswordHasher
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import RefreshToken
from app.modules.organizations.models import Membership, Organization
from app.modules.users.models import User
from app.modules.users.schemas import (
    ActiveMembership,
    UserMeResponse,
)

_MIN_PASSWORD_LENGTH = 8




class UserService:
    def __init__(self, password_hasher: PasswordHasher) -> None:
        self._password_hasher = password_hasher

    # -- self-service ---------------------------------------------------------

    async def get_me(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        permissions: frozenset[str],
    ) -> UserMeResponse:
        user = await session.get(User, user_id)
        if user is None or user.deleted_at is not None:
            raise APIError(401, "INVALID_TOKEN")
        membership = await self._active_membership(session, user_id, tenant_id)
        org = await session.get(Organization, tenant_id)
        if membership is None or org is None:
            raise APIError(403, "NO_ACTIVE_MEMBERSHIP")
        return UserMeResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            mfa_enabled=user.mfa_enabled,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            permissions=sorted(permissions),
            tenant_id=tenant_id,
            tenant_name=org.name,
            active_membership=ActiveMembership(
                id=membership.id,
                organization_id=membership.organization_id,
                property_id=membership.property_id,
                role=membership.role,
                is_active=membership.is_active,
            ),
        )

    async def update_me(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        permissions: frozenset[str],
        updates: dict[str, object],
    ) -> UserMeResponse:
        user = await session.get(User, user_id)
        if user is None or user.deleted_at is not None:
            raise APIError(401, "INVALID_TOKEN")
        for field in ("full_name", "avatar_url"):
            if field in updates:
                value = updates[field]
                if value is not None and not isinstance(value, str):
                    raise APIError(422, "VALIDATION_ERROR", f"{field} must be a string")
                setattr(user, field, value)
        await session.commit()
        return await self.get_me(session, user_id, tenant_id, permissions)

    async def change_password(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_password: str,
        new_password: str,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        user = await session.get(User, user_id)
        if user is None or user.deleted_at is not None:
            raise APIError(401, "INVALID_TOKEN")
        if not self._password_hasher.verify(current_password, user.password_hash):
            raise APIError(400, "INVALID_CURRENT_PASSWORD", "Current password is incorrect")
        if len(new_password) < _MIN_PASSWORD_LENGTH:
            raise APIError(
                422, "WEAK_PASSWORD", f"Password must be at least {_MIN_PASSWORD_LENGTH} characters"
            )
        user.password_hash = self._password_hasher.hash(new_password)
        await self._revoke_all_sessions(session, user_id)
        self._record_audit(
            session, user_id, tenant_id, "user.password.change", "user", user_id, ip, user_agent
        )
        await session.commit()

    # -- helpers --------------------------------------------------------------

    async def _active_membership(
        self, session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Membership | None:
        return (
            (
                await session.execute(
                    select(Membership).where(
                        Membership.user_id == user_id,
                        Membership.organization_id == tenant_id,
                        Membership.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .first()
        )

    async def _revoke_all_sessions(self, session: AsyncSession, user_id: uuid.UUID) -> None:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
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
