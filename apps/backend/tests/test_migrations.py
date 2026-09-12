"""Schema introspection and migration smoke tests for Phase 1 (DB & migrations).

Covers TASK-010..014 acceptance: tenant columns, indexes, FKs (including the
refresh-token chain), RBAC constraints + seeding, and append-only audit.
"""

import asyncio
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

import pytest
from alembic.config import Config
from sqlalchemy import column, delete, func, insert, inspect, select, table, update
from sqlalchemy.engine import Inspector
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import command as alembic_command

ALL_TABLES = {
    "users",
    "organizations",
    "properties",
    "memberships",
    "refresh_tokens",
    "mfa_devices",
    "sessions",
    "permissions",
    "roles",
    "role_permissions",
    "user_roles",
    "audit_events",
}

T = TypeVar("T")


async def _inspect(engine: AsyncEngine, fn: Callable[[Inspector], T]) -> T:
    async with engine.connect() as conn:
        return await conn.run_sync(lambda c: fn(inspect(c)))


def _tables_sync(engine: AsyncEngine) -> set[str]:
    return asyncio.run(_inspect(engine, lambda i: set(i.get_table_names())))


def _index_by_name(indexes: Sequence[Any], name: str) -> Any:
    for ix in indexes:
        if ix["name"] == name:
            return ix
    raise AssertionError(f"index {name!r} not found")


def test_migrations_upgrade_downgrade_smoke(
    alembic_cfg: Config, migrated_engine: AsyncEngine
) -> None:
    """TASK-010: upgrade -> downgrade -> upgrade round-trips cleanly."""
    alembic_command.downgrade(alembic_cfg, "base")
    assert _tables_sync(migrated_engine) <= {"alembic_version"}

    alembic_command.upgrade(alembic_cfg, "head")
    assert ALL_TABLES <= _tables_sync(migrated_engine)

    alembic_command.downgrade(alembic_cfg, "base")
    assert _tables_sync(migrated_engine) <= {"alembic_version"}

    alembic_command.upgrade(alembic_cfg, "head")
    assert "audit_events" in _tables_sync(migrated_engine)


async def test_core_tenant_columns_and_fks(migrated_engine: AsyncEngine) -> None:
    """TASK-011: tenant scoping via organization_id, with FKs and indexes."""
    m_fks = await _inspect(migrated_engine, lambda i: i.get_foreign_keys("memberships"))
    fk_refs = {(fk["constrained_columns"][0], fk["referred_table"]) for fk in m_fks}
    assert ("organization_id", "organizations") in fk_refs
    assert ("user_id", "users") in fk_refs
    assert ("property_id", "properties") in fk_refs

    p_fks = await _inspect(migrated_engine, lambda i: i.get_foreign_keys("properties"))
    assert any(fk["constrained_columns"] == ["organization_id"] for fk in p_fks)

    u_indexes = await _inspect(migrated_engine, lambda i: i.get_indexes("users"))
    assert _index_by_name(u_indexes, "ux_users_email")["unique"] is True

    m_indexes = await _inspect(migrated_engine, lambda i: i.get_indexes("memberships"))
    assert _index_by_name(m_indexes, "ux_memberships_user_org")["unique"] is True


async def test_refresh_token_chain_self_fk(migrated_engine: AsyncEngine) -> None:
    """TASK-012: refresh_tokens has a self-referential chain FK."""
    fks = await _inspect(migrated_engine, lambda i: i.get_foreign_keys("refresh_tokens"))
    self_fks = [fk for fk in fks if fk["referred_table"] == "refresh_tokens"]
    assert self_fks, "refresh_tokens must reference itself"
    assert self_fks[0]["constrained_columns"] == ["replaced_by_token_id"]

    s_fks = await _inspect(migrated_engine, lambda i: i.get_foreign_keys("sessions"))
    assert any(fk["referred_table"] == "refresh_tokens" for fk in s_fks)


async def test_rbac_constraints_and_seed(migrated_engine: AsyncEngine) -> None:
    """TASK-013: unique resource.action, cascade rules, and seed coverage."""
    p_indexes = await _inspect(migrated_engine, lambda i: i.get_indexes("permissions"))
    assert _index_by_name(p_indexes, "ux_permissions_name")["unique"] is True

    rp_fks = await _inspect(migrated_engine, lambda i: i.get_foreign_keys("role_permissions"))
    by_col = {fk["constrained_columns"][0]: fk for fk in rp_fks}
    assert by_col["role_id"]["options"]["ondelete"] == "CASCADE"
    assert by_col["permission_id"]["options"]["ondelete"] == "CASCADE"

    roles_t = table("roles", column("id"), column("name"))
    rp_t = table("role_permissions", column("role_id"), column("permission_id"))

    async with migrated_engine.connect() as conn:
        perms = (
            await conn.execute(select(func.count()).select_from(table("permissions")))
        ).scalar_one()
        roles = (await conn.execute(select(func.count()).select_from(table("roles")))).scalar_one()
        joined = rp_t.join(roles_t, rp_t.c.role_id == roles_t.c.id)
        super_admin = (
            await conn.execute(
                select(func.count()).select_from(joined).where(roles_t.c.name == "super_admin")
            )
        ).scalar_one()
        org_admin = (
            await conn.execute(
                select(func.count()).select_from(joined).where(roles_t.c.name == "org_admin")
            )
        ).scalar_one()

    assert perms == 34
    assert roles == 10
    assert super_admin == 34
    assert org_admin == 27


async def test_audit_schema_and_append_only(migrated_engine: AsyncEngine) -> None:
    """TASK-014: full audit columns, tenant FK, and append-only enforcement."""
    cols = await _inspect(
        migrated_engine, lambda i: {c["name"] for c in i.get_columns("audit_events")}
    )
    assert {
        "id",
        "actor_user_id",
        "tenant_id",
        "action",
        "resource",
        "resource_id",
        "timestamp",
        "ip",
        "user_agent",
        "metadata",
    } <= cols

    a_fks = await _inspect(migrated_engine, lambda i: i.get_foreign_keys("audit_events"))
    fk_refs = {(fk["constrained_columns"][0], fk["referred_table"]) for fk in a_fks}
    assert ("tenant_id", "organizations") in fk_refs
    assert ("actor_user_id", "users") in fk_refs

    users_t = table("users", column("id"), column("email"), column("password_hash"))
    orgs_t = table("organizations", column("id"), column("name"), column("slug"))
    audit_t = table(
        "audit_events",
        column("actor_user_id"),
        column("tenant_id"),
        column("action"),
        column("resource"),
    )

    async with migrated_engine.connect() as conn:
        uid = (
            await conn.execute(
                insert(users_t).values(email="a@x.io", password_hash="h").returning(users_t.c.id)
            )
        ).scalar_one()
        oid = (
            await conn.execute(insert(orgs_t).values(name="o", slug="o").returning(orgs_t.c.id))
        ).scalar_one()
        await conn.execute(
            insert(audit_t).values(
                actor_user_id=uid, tenant_id=oid, action="user.login", resource="user"
            )
        )
        await conn.commit()

        with pytest.raises(DBAPIError, match="append-only"):
            await conn.execute(update(audit_t).values(action="x"))
        await conn.rollback()

        with pytest.raises(DBAPIError, match="append-only"):
            await conn.execute(delete(audit_t))
        await conn.rollback()
