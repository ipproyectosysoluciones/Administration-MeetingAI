"""TASK-045: session management GET/DELETE /users/me/sessions.

Integration tests against PostgreSQL. Covers listing sessions with the current
session flagged (the one whose refresh token matches the httpOnly cookie), revoking
a non-current session (others stay valid), revoking the current session (logout), and
the 404 / 401 error paths. A second active session is injected directly via the DB to
simulate another device without entangling these tests with the MFA gate.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.auth.models import RefreshToken, Session
from app.modules.users.models import User


def _payload(**overrides: str) -> dict[str, str]:
    payload: dict[str, str] = {
        "email": f"admin-{uuid.uuid4()}@example.com",
        "password": "securePassword123",
        "full_name": "Juan Pérez",
        "organization_name": "Conjunto Residencial Los Pinos",
        "organization_slug": f"los-pinos-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    return payload


async def _register(auth_app: FastAPI) -> tuple[httpx.Response, httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=auth_app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    resp = await client.post("/api/v1/auth/register", json=_payload())
    assert resp.status_code == 201, resp.text
    return resp, client


async def _add_foreign_session(
    session_factory: async_sessionmaker, email: str, *, ip: str = "1.2.3.4"
) -> uuid.UUID:
    """Insert a second active session (another device) directly into the DB."""
    async with session_factory() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        token = RefreshToken(
            user_id=user.id,
            token_hash=f"fixture-{uuid.uuid4().hex}",
            expires_at=datetime.now(UTC) + timedelta(days=30),
            ip=ip,
            user_agent="Device-B/1.0",
        )
        db.add(token)
        await db.flush()
        sess = Session(user_id=user.id, refresh_token_id=token.id, ip=ip, user_agent="Device-B/1.0")
        db.add(sess)
        await db.commit()
        return sess.id


def _current_id(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [i for i in items if i["is_current"] is True]


async def test_list_sessions_flags_current_session(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    reg, client = await _register(auth_app)
    payload = reg.json()
    await client.aclose()
    access = payload["access_token"]
    refresh_cookie = reg.cookies["refresh_token"]
    email = payload["user"]["email"]

    await _add_foreign_session(session_factory, email)

    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(
            "/api/v1/users/me/sessions",
            headers={"Authorization": f"Bearer {access}"},
            cookies={"refresh_token": refresh_cookie},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pages"] == 1
    items = body["items"]
    assert len(items) == 2
    assert len(_current_id(items)) == 1


async def test_revoke_other_session_keeps_current_valid(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    reg, client = await _register(auth_app)
    access = reg.json()["access_token"]
    refresh_cookie = reg.cookies["refresh_token"]
    email = reg.json()["user"]["email"]
    await client.aclose()

    foreign_id = await _add_foreign_session(session_factory, email)

    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        listing = await c.get(
            "/api/v1/users/me/sessions",
            headers={"Authorization": f"Bearer {access}"},
            cookies={"refresh_token": refresh_cookie},
        )
        items = listing.json()["items"]
        others = [i for i in items if i["is_current"] is False]
        assert len(others) == 1
        assert uuid.UUID(str(others[0]["id"])) == foreign_id

        deleted = await c.delete(
            f"/api/v1/users/me/sessions/{foreign_id}",
            headers={"Authorization": f"Bearer {access}"},
            cookies={"refresh_token": refresh_cookie},
        )
        assert deleted.status_code == 200, deleted.text

        # The current session's refresh token must remain valid.
        refresh = await c.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_cookie})
        assert refresh.status_code == 200, refresh.text


async def test_revoke_current_session_logs_out(auth_app: FastAPI) -> None:
    reg, client = await _register(auth_app)
    access = reg.json()["access_token"]
    refresh_cookie = reg.cookies["refresh_token"]

    listing = await client.get(
        "/api/v1/users/me/sessions",
        headers={"Authorization": f"Bearer {access}"},
        cookies={"refresh_token": refresh_cookie},
    )
    items = listing.json()["items"]
    assert len(items) == 1
    current = items[0]
    assert current["is_current"] is True

    deleted = await client.delete(
        f"/api/v1/users/me/sessions/{current['id']}",
        headers={"Authorization": f"Bearer {access}"},
        cookies={"refresh_token": refresh_cookie},
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"message": "Session revoked"}

    refresh = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert refresh.status_code == 401

    await client.aclose()


async def test_revoke_unknown_session_returns_404(auth_app: FastAPI) -> None:
    reg, client = await _register(auth_app)
    access = reg.json()["access_token"]

    resp = await client.delete(
        f"/api/v1/users/me/sessions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "SESSION_NOT_FOUND"

    await client.aclose()


async def test_sessions_require_auth(auth_app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        listing = await client.get("/api/v1/users/me/sessions")
        assert listing.status_code == 401

        deleted = await client.delete(f"/api/v1/users/me/sessions/{uuid.uuid4()}")
        assert deleted.status_code == 401
