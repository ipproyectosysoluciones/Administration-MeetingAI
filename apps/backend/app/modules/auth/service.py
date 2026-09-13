"""Auth service: registration, login, refresh rotation, and revocation (PR-3a).

Tenant + permissions are always derived server-side via
``rbac.resolver.resolve_auth_context`` — never from a request-supplied ``tenant_id``
(reunionai-multitenant-security). Refresh tokens are opaque 256-bit values stored
only as SHA-256 digests, rotated on every use, with reuse detection that revokes the
whole chain (architecture §4.2).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import APIError, TenantResolutionError
from app.core.security import JWTService, PasswordHasher
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import RefreshToken, Session
from app.modules.organizations.models import Membership, Organization
from app.modules.rbac.models import Role, UserRole
from app.modules.rbac.resolver import resolve_auth_context
from app.modules.users.models import User

ORG_ADMIN_ROLE = "org_admin"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


@dataclass
class AuthResult:
    """Tokens + identity resolved by a successful auth operation.

    ``refresh_token`` is the *plaintext* token, used only to set the httpOnly cookie
    at the router layer — it is never serialized into a response body.
    """

    access_token: str
    refresh_token: str
    expires_in: int
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    permissions: frozenset[str]
    email: str
    full_name: str | None
    is_active: bool
    mfa_enabled: bool


class AuthService:
    def __init__(
        self,
        settings: Settings,
        password_hasher: PasswordHasher,
        jwt_service: JWTService,
    ) -> None:
        self._settings = settings
        self._password_hasher = password_hasher
        self._jwt_service = jwt_service

    # -- registration ---------------------------------------------------------

    async def register(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        full_name: str,
        organization_name: str,
        organization_slug: str,
        ip: str | None,
        user_agent: str | None,
    ) -> AuthResult:
        email = email.strip().lower()
        existing = (
            await session.execute(select(User.id).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            raise APIError(409, "EMAIL_EXISTS", "Email already registered")

        org = Organization(name=organization_name, slug=organization_slug)
        session.add(org)
        await session.flush()

        user = User(
            email=email,
            password_hash=self._password_hasher.hash(password),
            full_name=full_name,
        )
        session.add(user)
        await session.flush()

        session.add(Membership(user_id=user.id, organization_id=org.id, role=ORG_ADMIN_ROLE))
        org_admin_role = (
            await session.execute(
                select(Role).where(Role.name == ORG_ADMIN_ROLE, Role.organization_id.is_(None))
            )
        ).scalar_one()
        session.add(UserRole(user_id=user.id, role_id=org_admin_role.id, organization_id=org.id))
        await session.flush()

        result = await self._issue(session, user, ip, user_agent)
        self._record_audit(
            session, user.id, org.id, "auth.register", "user", user.id, ip, user_agent
        )
        await session.commit()
        return result

    # -- login ----------------------------------------------------------------

    async def login(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        ip: str | None,
        user_agent: str | None,
    ) -> AuthResult | None:
        email = email.strip().lower()
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None or not self._password_hasher.verify(password, user.password_hash):
            raise APIError(401, "INVALID_CREDENTIALS", "Invalid email or password")
        if not user.is_active or user.deleted_at is not None:
            raise APIError(403, "USER_INACTIVE", "User account is inactive")
        if user.mfa_enabled:
            return None  # hook: the full MFA challenge lands in slice 3b

        user.last_login_at = datetime.now(UTC)
        result = await self._issue(session, user, ip, user_agent)
        self._record_audit(
            session, user.id, result.tenant_id, "auth.login", "user", user.id, ip, user_agent
        )
        await session.commit()
        return result

    # -- refresh --------------------------------------------------------------

    async def refresh(
        self,
        session: AsyncSession,
        raw_token: str,
        ip: str | None,
        user_agent: str | None,
    ) -> AuthResult:
        token = (
            await session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token))
            )
        ).scalar_one_or_none()
        if token is None:
            raise APIError(401, "INVALID_REFRESH_TOKEN")

        now = datetime.now(UTC)
        if token.expires_at <= now:
            raise APIError(401, "INVALID_REFRESH_TOKEN")

        if token.revoked_at is not None or token.replaced_by_token_id is not None:
            token = await self._handle_reuse(session, token, now)

        return await self._rotate(session, token, ip, user_agent)

    async def _handle_reuse(
        self, session: AsyncSession, token: RefreshToken, now: datetime
    ) -> RefreshToken:
        grace = timedelta(seconds=self._settings.refresh_grace_seconds)
        replaced = token.replaced_by_token_id is not None
        within_grace = token.revoked_at is not None and (now - token.revoked_at) <= grace

        if replaced and within_grace:
            leaf = await self._live_leaf(session, token)
            if leaf is not None:
                return leaf

        await self._revoke_chain(session, token)
        # Persist the chain revocation before rejecting, so a replay genuinely
        # invalidates the live sibling too (scenario "replayed token revokes chain").
        await session.commit()
        if replaced:
            raise APIError(401, "REFRESH_TOKEN_REUSE_DETECTED")
        raise APIError(401, "INVALID_REFRESH_TOKEN")

    async def _live_leaf(self, session: AsyncSession, token: RefreshToken) -> RefreshToken | None:
        current: RefreshToken = token
        while current.replaced_by_token_id is not None:
            successor = await session.get(RefreshToken, current.replaced_by_token_id)
            if successor is None:
                return None
            current = successor
        if current.revoked_at is not None or current.expires_at <= datetime.now(UTC):
            return None
        return current

    async def _revoke_chain(self, session: AsyncSession, token: RefreshToken) -> None:
        now = datetime.now(UTC)
        current: RefreshToken | None = token
        while current is not None:
            if current.revoked_at is None:
                current.revoked_at = now
                session.add(current)
            next_id = current.replaced_by_token_id
            current = await session.get(RefreshToken, next_id) if next_id is not None else None
        await session.flush()

    async def _rotate(
        self,
        session: AsyncSession,
        token: RefreshToken,
        ip: str | None,
        user_agent: str | None,
    ) -> AuthResult:
        user = await session.get(User, token.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise APIError(401, "INVALID_REFRESH_TOKEN")

        raw = _new_refresh_token()
        new_token = RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(days=self._settings.refresh_ttl_days),
            ip=ip,
            user_agent=user_agent,
        )
        session.add(new_token)
        await session.flush()

        token.revoked_at = datetime.now(UTC)
        token.replaced_by_token_id = new_token.id
        session.add(
            Session(user_id=user.id, refresh_token_id=new_token.id, ip=ip, user_agent=user_agent)
        )

        result = await self._build_result(session, user, raw)
        await session.commit()
        return result

    # -- revoke ---------------------------------------------------------------

    async def revoke(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        raw_token: str,
        tenant_id: uuid.UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        token = (
            await session.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == _hash_token(raw_token),
                    RefreshToken.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if token is None or token.revoked_at is not None:
            raise APIError(401, "INVALID_TOKEN", "Refresh token not found or already revoked")
        token.revoked_at = datetime.now(UTC)
        self._record_audit(
            session, user_id, tenant_id, "auth.revoke", "session", token.id, ip, user_agent
        )
        await session.commit()

    # -- helpers --------------------------------------------------------------

    async def _issue(
        self, session: AsyncSession, user: User, ip: str | None, user_agent: str | None
    ) -> AuthResult:
        raw = _new_refresh_token()
        refresh = RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(days=self._settings.refresh_ttl_days),
            ip=ip,
            user_agent=user_agent,
        )
        session.add(refresh)
        await session.flush()
        session.add(
            Session(user_id=user.id, refresh_token_id=refresh.id, ip=ip, user_agent=user_agent)
        )
        return await self._build_result(session, user, raw)

    async def _build_result(self, session: AsyncSession, user: User, raw: str) -> AuthResult:
        try:
            context = await resolve_auth_context(session, user.id)
        except TenantResolutionError as exc:
            raise APIError(403, "NO_ACTIVE_MEMBERSHIP") from exc
        if context.tenant_id is None:
            raise APIError(403, "NO_ACTIVE_MEMBERSHIP")
        access = self._jwt_service.create_access_token(
            user.id, context.tenant_id, sorted(context.permissions)
        )
        return AuthResult(
            access_token=access,
            refresh_token=raw,
            expires_in=self._settings.jwt_access_ttl_minutes * 60,
            user_id=user.id,
            tenant_id=context.tenant_id,
            permissions=context.permissions,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            mfa_enabled=user.mfa_enabled,
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
