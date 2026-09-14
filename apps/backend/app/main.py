"""ReunionAI FastAPI application factory and entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import async_session_factory
from app.core.exceptions import APIError
from app.core.middleware.rate_limit import InMemoryRateLimiter
from app.core.security import JWTService, PasswordHasher
from app.modules.auth.router import router as auth_router
from app.modules.organizations.router import router as organizations_router
from app.modules.rbac.resolver import DBAuthorizationResolver
from app.modules.rbac.roles_router import router as rbac_roles_router
from app.modules.users.router import router as users_router


def create_app(
    settings: Settings | None = None,
    session_factory: async_sessionmaker | None = None,
) -> FastAPI:
    """Build the FastAPI application.

    ``settings`` and ``session_factory`` are injectable so tests can run against a
    dedicated database and an ephemeral RS256 keypair; when omitted, defaults come
    from the environment (``get_settings``) and the global async session factory.
    """
    settings = settings or get_settings()
    session_factory = session_factory or async_session_factory

    app = FastAPI(title="ReunionAI API", version="0.1.0")
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.password_hasher = PasswordHasher(settings)
    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.authorization_resolver = DBAuthorizationResolver(session_factory)

    # JWT keys may legitimately be absent (e.g. the health-check surface in tests);
    # auth endpoints raise a clean JWT_NOT_CONFIGURED error in that case.
    try:
        app.state.jwt_service = JWTService(settings)
    except ValueError:
        app.state.jwt_service = None

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(organizations_router, prefix="/api/v1")
    app.include_router(rbac_roles_router, prefix="/api/v1")

    @app.exception_handler(APIError)
    async def _api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
