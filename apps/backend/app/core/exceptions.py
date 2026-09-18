"""Domain exceptions for the security primitive layer (`architecture.md` §2.1).

These are raised by ``core`` primitives and mapped to HTTP status codes at the
dependency/router layer: ``InvalidTokenError``/``ExpiredTokenError`` → 401,
``AuthorizationError`` → 403, ``TenantResolutionError`` → 403/404 as appropriate.
"""

from __future__ import annotations


class SecurityError(Exception):
    """Base class for authentication/authorization failures."""


class TokenError(SecurityError):
    """Base class for JWT validation failures."""


class InvalidTokenError(TokenError):
    """Signature or format is invalid (wrong key, tampered, or malformed)."""


class ExpiredTokenError(TokenError):
    """Token is past its ``exp`` claim."""


class AuthenticationError(SecurityError):
    """No valid authenticated identity (maps to HTTP 401)."""


class AuthorizationError(SecurityError):
    """Authenticated but not permitted for the requested action (HTTP 403)."""


class TenantResolutionError(SecurityError):
    """No active membership/tenant could be resolved for the user (HTTP 403)."""


class APIError(Exception):
    """Domain error carrying an HTTP status and a stable machine-readable ``code``.

    The handler in ``app.main`` serializes this to ``{"code": ..., "message": ...}``
    (api-contract.md §7 error reference), keeping error shapes uniform across modules.
    """

    def __init__(self, status_code: int, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.status_code = status_code
        self.code = code
        self.message = message or code


__all__ = [
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "ExpiredTokenError",
    "InvalidTokenError",
    "SecurityError",
    "TenantResolutionError",
    "TokenError",
]
