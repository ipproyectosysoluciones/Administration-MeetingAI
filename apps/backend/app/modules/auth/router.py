"""Auth routes: /auth/register, /auth/login, /auth/refresh, /auth/revoke (PR-3a).

Rate limiting on register/login/refresh reuses the PR-2 ``InMemoryRateLimiter``.
Refresh tokens travel only in the ``httpOnly`` cookie (never in request/response
bodies); access tokens are returned in the JSON body.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import AuthContext, get_db, require_auth
from app.core.exceptions import APIError
from app.core.middleware.rate_limit import InMemoryRateLimiter
from app.core.security import JWTService
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.modules.auth.service import AuthResult, AuthService

router = APIRouter(tags=["auth"])

REFRESH_COOKIE = "refresh_token"

Db = Annotated[AsyncSession, Depends(get_db)]
Authenticated = Annotated[AuthContext, Depends(require_auth())]


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _service(request: Request) -> AuthService:
    settings: Settings = request.app.state.settings
    jwt_service: JWTService | None = request.app.state.jwt_service
    if jwt_service is None:
        raise APIError(500, "JWT_NOT_CONFIGURED", "JWT keys are not configured")
    return AuthService(
        settings=settings,
        password_hasher=request.app.state.password_hasher,
        jwt_service=jwt_service,
    )


def _check_rate_limit(request: Request, scope: str, key: str, limit: int) -> None:
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    if not limiter.is_allowed(scope, key, limit, 60.0):
        raise APIError(429, "RATE_LIMITED", "Too many requests")


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.refresh_ttl_days * 86400,
        path="/api/v1/auth",
    )


def _token_response(result: AuthResult) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        user=UserResponse(
            id=result.user_id,
            email=result.email,
            full_name=result.full_name,
            is_active=result.is_active,
            mfa_enabled=result.mfa_enabled,
            permissions=sorted(result.permissions),
            tenant_id=result.tenant_id,
        ),
    )


@router.post("/auth/register", status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Db,
) -> TokenResponse:
    settings: Settings = request.app.state.settings
    _check_rate_limit(
        request, "register", _ip(request) or "unknown", settings.rate_limit_register_ip
    )
    result = await _service(request).register(
        db,
        payload.email,
        payload.password,
        payload.full_name,
        payload.organization_name,
        payload.organization_slug,
        _ip(request),
        _user_agent(request),
    )
    _set_refresh_cookie(response, result.refresh_token, settings)
    return _token_response(result)


@router.post("/auth/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Db,
) -> TokenResponse | dict[str, object]:
    settings: Settings = request.app.state.settings
    ip = _ip(request) or "unknown"
    _check_rate_limit(request, "login", ip, settings.rate_limit_login_ip)
    _check_rate_limit(
        request, "login:user", payload.email.strip().lower(), settings.rate_limit_login_user
    )
    result = await _service(request).login(
        db, payload.email, payload.password, _ip(request), _user_agent(request)
    )
    if result is None:
        return {"mfa_required": True, "message": "MFA verification required"}
    _set_refresh_cookie(response, result.refresh_token, settings)
    return _token_response(result)


@router.post("/auth/refresh")
async def refresh(request: Request, response: Response, db: Db) -> TokenResponse:
    settings: Settings = request.app.state.settings
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_token:
        raise APIError(401, "INVALID_REFRESH_TOKEN", "Refresh token missing")
    _check_rate_limit(request, "refresh", _ip(request) or "unknown", settings.rate_limit_refresh_ip)
    result = await _service(request).refresh(db, raw_token, _ip(request), _user_agent(request))
    _set_refresh_cookie(response, result.refresh_token, settings)
    return _token_response(result)


@router.post("/auth/revoke")
async def revoke(request: Request, db: Db, context: Authenticated) -> dict[str, str]:
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_token:
        raise APIError(401, "INVALID_TOKEN", "Refresh token missing")
    if context.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP")
    await _service(request).revoke(
        db, context.user_id, raw_token, context.tenant_id, _ip(request), _user_agent(request)
    )
    return {"message": "Session revoked successfully"}
