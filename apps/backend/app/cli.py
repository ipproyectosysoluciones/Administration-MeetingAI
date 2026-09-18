"""Platform super-admin bootstrap CLI (TASK-111).

Creates the first platform super-admin (``is_super_admin`` user with a platform
organization) and writes an audited event. Idempotent: re-running is a no-op.

Usage:
    python -m app.cli bootstrap-superadmin --email admin@example.com \
        --password <secret> --full-name "Platform Admin"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import PasswordHasher
from app.modules.audit.models import AuditEvent
from app.modules.organizations.models import Organization
from app.modules.users.models import User

PLATFORM_ORG_NAME = "Platform"
PLATFORM_ORG_SLUG = "platform"


async def bootstrap_superadmin(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
) -> tuple[uuid.UUID | None, bool]:
    """Create the platform super-admin. Returns (user_id, created).

    Idempotent: if a super-admin already exists, returns (None, False) and writes
    nothing.
    """
    existing = (
        (await session.execute(select(User).where(User.is_super_admin.is_(True)))).scalars().first()
    )
    if existing is not None:
        return None, False

    session_factory_tenant = (
        await session.execute(select(Organization).where(Organization.slug == PLATFORM_ORG_SLUG))
    ).scalar_one_or_none()
    if session_factory_tenant is None:
        session_factory_tenant = Organization(name=PLATFORM_ORG_NAME, slug=PLATFORM_ORG_SLUG)
        session.add(session_factory_tenant)
        await session.flush()

    user = User(
        email=email.strip().lower(),
        password_hash=PasswordHasher().hash(password),
        full_name=full_name,
        is_super_admin=True,
    )
    session.add(user)
    await session.flush()

    session.add(
        AuditEvent(
            actor_user_id=user.id,
            tenant_id=session_factory_tenant.id,
            action="platform.super_admin.bootstrap",
            resource="user",
            resource_id=user.id,
            metadata_json={"source": "cli"},
        )
    )
    await session.commit()
    return user.id, True


async def _run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reunionai-cli")
    sub = parser.add_subparsers(dest="command", required=True)
    boot = sub.add_parser("bootstrap-superadmin", help="Create the first platform super-admin")
    boot.add_argument("--email", required=True)
    boot.add_argument("--password", required=True)
    boot.add_argument("--full-name", required=True)
    args = parser.parse_args(argv)

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        user_id, created = await bootstrap_superadmin(
            session,
            email=args.email,
            password=args.password,
            full_name=args.full_name,
        )
    await engine.dispose()

    if created:
        print(f"Super-admin created: {user_id} ({args.email})")
    else:
        print("Super-admin already exists; no changes made.")
    return 0


def main() -> None:
    sys.exit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
