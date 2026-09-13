"""Pydantic request/response models for the auth module (api-contract.md §2)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    organization_name: str
    organization_slug: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    mfa_enabled: bool
    permissions: list[str]
    tenant_id: uuid.UUID | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    mfa_required: bool = False


class MfaSetupResponse(BaseModel):
    secret: str
    qr_code_uri: str
    backup_codes: list[str]


class MfaVerifyRequest(BaseModel):
    code: str


class MfaDisableRequest(BaseModel):
    password: str


class MfaChallengeRequest(BaseModel):
    code: str


class MfaStatusResponse(BaseModel):
    message: str
    mfa_enabled: bool
