"""TASK-044: MFA TOTP endpoints — setup/verify/disable/challenge + single-use recovery codes.

Integration tests against PostgreSQL (same fixtures as ``test_login.py``). Covers the
full enrollment lifecycle (setup → verify → login challenge), single-use recovery codes,
and password-gated disable. TOTP codes are generated with the same ``TOTP`` service the
endpoints use, so these exercise the whole HTTP flow, not the RFC 6238 math.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import TOTP
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


async def _post(
    app: FastAPI, path: str, json: dict[str, str] | None = None, token: str | None = None
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=json, headers=headers)


async def _register(app: FastAPI, payload: dict[str, str]) -> str:
    resp = await _post(app, "/api/v1/auth/register", payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def _setup_mfa(app: FastAPI, token: str) -> httpx.Response:
    return await _post(app, "/api/v1/auth/mfa/setup", token=token)


async def _verify_mfa(app: FastAPI, token: str, code: str) -> httpx.Response:
    return await _post(app, "/api/v1/auth/mfa/verify", {"code": code}, token=token)


async def _enroll(app: FastAPI, token: str, secret: str) -> None:
    resp = await _verify_mfa(app, token, TOTP.current_code(secret))
    assert resp.status_code == 200, resp.text


async def _login(app: FastAPI, email: str, password: str) -> httpx.Response:
    return await _post(app, "/api/v1/auth/login", {"email": email, "password": password})


async def test_mfa_setup_returns_secret_and_backup_codes(auth_app: FastAPI) -> None:
    payload = _payload()
    token = await _register(auth_app, payload)

    resp = await _setup_mfa(auth_app, token)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["secret"]
    assert body["qr_code_uri"].startswith("otpauth://totp/ReunionAI:")
    assert len(body["backup_codes"]) == 8


async def test_mfa_verify_rejects_wrong_code_then_enables(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    payload = _payload()
    token = await _register(auth_app, payload)
    secret = (await _setup_mfa(auth_app, token)).json()["secret"]

    bad = await _verify_mfa(auth_app, token, "000000")
    assert bad.status_code == 400
    assert bad.json()["code"] == "INVALID_TOTP_CODE"

    good = await _verify_mfa(auth_app, token, TOTP.current_code(secret))
    assert good.status_code == 200, good.text
    assert good.json()["mfa_enabled"] is True

    async with session_factory() as session:
        stmt = select(User).where(User.email == payload["email"])
        user = (await session.execute(stmt)).scalar_one()
        assert user.mfa_enabled is True
        assert user.mfa_secret == secret


async def test_mfa_challenge_issues_full_tokens_after_login(auth_app: FastAPI) -> None:
    payload = _payload()
    token = await _register(auth_app, payload)
    secret = (await _setup_mfa(auth_app, token)).json()["secret"]
    await _enroll(auth_app, token, secret)

    login = await _login(auth_app, payload["email"], payload["password"])
    assert login.status_code == 200, login.text
    assert login.json()["mfa_required"] is True
    mfa_token = login.json()["mfa_token"]
    assert "access_token" not in login.json()

    challenge = await _post(
        auth_app, "/api/v1/auth/mfa/challenge", {"code": TOTP.current_code(secret)}, mfa_token
    )

    assert challenge.status_code == 200, challenge.text
    body = challenge.json()
    assert body["access_token"]
    assert body["user"]["email"] == payload["email"]
    assert "refresh_token" in challenge.cookies


async def test_recovery_code_is_single_use(auth_app: FastAPI) -> None:
    payload = _payload()
    token = await _register(auth_app, payload)
    setup = (await _setup_mfa(auth_app, token)).json()
    await _enroll(auth_app, token, setup["secret"])

    login = await _login(auth_app, payload["email"], payload["password"])
    mfa_token = login.json()["mfa_token"]
    recovery_code = setup["backup_codes"][0]

    first = await _post(auth_app, "/api/v1/auth/mfa/challenge", {"code": recovery_code}, mfa_token)
    assert first.status_code == 200, first.text
    assert first.json()["access_token"]

    login = await _login(auth_app, payload["email"], payload["password"])
    second = await _post(
        auth_app, "/api/v1/auth/mfa/challenge", {"code": recovery_code}, login.json()["mfa_token"]
    )
    assert second.status_code == 400
    assert second.json()["code"] == "INVALID_TOTP_CODE"


async def test_mfa_disable_requires_password(auth_app: FastAPI) -> None:
    payload = _payload()
    token = await _register(auth_app, payload)
    secret = (await _setup_mfa(auth_app, token)).json()["secret"]
    await _enroll(auth_app, token, secret)

    wrong = await _post(
        app=auth_app, path="/api/v1/auth/mfa/disable", json={"password": "nope"}, token=token
    )
    assert wrong.status_code == 400
    assert wrong.json()["code"] == "INVALID_PASSWORD"

    ok = await _post(
        app=auth_app,
        path="/api/v1/auth/mfa/disable",
        json={"password": payload["password"]},
        token=token,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["mfa_enabled"] is False


async def test_mfa_challenge_rejects_wrong_code(auth_app: FastAPI) -> None:
    payload = _payload()
    token = await _register(auth_app, payload)
    secret = (await _setup_mfa(auth_app, token)).json()["secret"]
    await _enroll(auth_app, token, secret)

    login = await _login(auth_app, payload["email"], payload["password"])
    mfa_token = login.json()["mfa_token"]

    wrong = await _post(auth_app, "/api/v1/auth/mfa/challenge", {"code": "000000"}, mfa_token)

    assert wrong.status_code == 400
    assert wrong.json()["code"] == "INVALID_TOTP_CODE"
    assert "access_token" not in wrong.json()


async def test_mfa_setup_rejects_when_already_enabled(auth_app: FastAPI) -> None:
    payload = _payload()
    token = await _register(auth_app, payload)
    secret = (await _setup_mfa(auth_app, token)).json()["secret"]
    await _enroll(auth_app, token, secret)

    again = await _setup_mfa(auth_app, token)

    assert again.status_code == 403
    assert again.json()["code"] == "MFA_ALREADY_ENABLED"


async def test_mfa_endpoints_require_auth(auth_app: FastAPI) -> None:
    resp = await _post(auth_app, "/api/v1/auth/mfa/setup")
    assert resp.status_code == 401
