# API Contract: auth-multitenant-foundation

**Change ID:** `auth-multitenant-foundation`
**Status:** Design
**Date:** 2025-01-15
**Base Path:** `/api/v1`

---

## 1. Conventions

- **Authentication:** Bearer token (JWT access token) unless noted.
- **Refresh Token:** Sent via `httpOnly` cookie (`refresh_token`); not in body.
- **Tenant Scoping:** Automatic via `tenant_id` from authenticated user's active membership. Never passed by client.
- **Permissions:** Enforced via `require_permission("resource.action")` dependency. Returns 401 (unauthenticated), 403 (unauthorized), 404 (cross-tenant/resource not found).
- **Rate Limits:** Per-IP and per-user on auth endpoints (see architecture.md §7).
- **Errors:** Standard format:

  ```json
  { "detail": "Human-readable message", "code": "ERROR_CODE", "meta": {} }
  ```

- **Pagination:** `?page=1&page_size=20` (max 100). Response:

  ```json
  { "items": [], "total": 0, "page": 1, "page_size": 20, "pages": 1 }
  ```

- **Timestamps:** ISO 8601 UTC (`2025-01-15T10:30:00Z`).
- **UUIDs:** Lowercase with hyphens (`550e8400-e29b-41d4-a716-446655440000`).

---

## 2. Auth Module

### 2.1 POST `/auth/register`

**Auth:** None
**Rate Limit:** IP: 3/min
**Description:** Self-service registration. Creates organization + Organization Admin user + membership. Returns tokens.

**Request:**

```json
{
  "email": "admin@example.com",
  "password": "securePassword123",
  "full_name": "Juan Pérez",
  "organization_name": "Conjunto Residencial Los Pinos",
  "organization_slug": "los-pinos"
}
```

**Response 201:**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "admin@example.com",
    "full_name": "Juan Pérez",
    "is_active": true,
    "mfa_enabled": false,
    "permissions": ["organization.read", "user.read", "membership.read", "audit.read", ...],
    "tenant_id": "660e8400-e29b-41d4-a716-446655440001"
  }
}
```

*Refresh token set in `httpOnly` cookie.*

**Errors:**

- `409 CONFLICT` — Email already exists (code: `EMAIL_EXISTS`)
- `422 VALIDATION_ERROR` — Invalid input (code: `VALIDATION_ERROR`)
- `429 TOO_MANY_REQUESTS` — Rate limited (code: `RATE_LIMITED`)

---

### 2.2 POST `/auth/login`

**Auth:** None
**Rate Limit:** IP: 5/min, User: 20/min
**Description:** Authenticate user. Returns tokens or MFA challenge.

**Request:**

```json
{
  "email": "admin@example.com",
  "password": "securePassword123"
}
```

**Response 200 (No MFA):**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { ... },
  "mfa_required": false
}
```

**Response 200 (MFA Required):**

```json
{
  "mfa_required": true,
  "mfa_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...", // 5-min TTL
  "message": "MFA verification required"
}
```

**Errors:**

- `401 UNAUTHORIZED` — Invalid credentials (code: `INVALID_CREDENTIALS`)
- `403 FORBIDDEN` — User inactive/soft-deleted (code: `USER_INACTIVE`)
- `403 FORBIDDEN` — Admin role requires MFA not enabled (code: `MFA_REQUIRED_FOR_ROLE`)
- `429 TOO_MANY_REQUESTS` — Rate limited (code: `RATE_LIMITED`)

---

### 2.3 POST `/auth/refresh`

**Auth:** Refresh token cookie (required)
**Rate Limit:** IP: 30/min, User: 60/min
**Description:** Rotate access + refresh token. Detects reuse → revokes chain.

**Request:** Empty body (cookie provides refresh token)

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { ... }
}
```

*New refresh token set in cookie.*

**Errors:**

- `401 UNAUTHORIZED` — Invalid/expired/revoked/reused refresh token (code: `INVALID_REFRESH_TOKEN`)
- `401 UNAUTHORIZED` — Refresh token reuse detected, chain revoked (code: `REFRESH_TOKEN_REUSE_DETECTED`)
- `429 TOO_MANY_REQUESTS` — Rate limited (code: `RATE_LIMITED`)

---

### 2.4 POST `/auth/revoke`

**Auth:** Access token (Bearer)
**Permission:** `auth.revoke` (self)
**Description:** Revoke current refresh token (logout).

**Request:** Empty body

**Response 200:**

```json
{ "message": "Session revoked successfully" }
```

**Errors:**

- `401 UNAUTHORIZED` — Invalid access token (code: `INVALID_TOKEN`)

---

### 2.5 POST `/auth/mfa/setup`

**Auth:** Access token
**Permission:** `auth.mfa.manage` (self)
**Description:** Initiate TOTP enrollment. Returns secret + QR URI.

**Request:** Empty body

**Response 200:**

```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_uri": "otpauth://totp/ReunionAI:admin@example.com?secret=JBSWY3DPEHPK3PXP&issuer=ReunionAI",
  "backup_codes": ["12345678", "87654321", ...] // 8 codes, shown once
}
```

**Errors:**

- `403 FORBIDDEN` — MFA already enabled (code: `MFA_ALREADY_ENABLED`)
- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)

---

### 2.6 POST `/auth/mfa/verify`

**Auth:** Access token
**Permission:** `auth.mfa.manage` (self)
**Description:** Verify TOTP code to enable MFA.

**Request:**

```json
{ "code": "123456" }
```

**Response 200:**

```json
{ "message": "MFA enabled successfully", "mfa_enabled": true }
```

**Errors:**

- `400 BAD_REQUEST` — Invalid TOTP code (code: `INVALID_TOTP_CODE`)
- `403 FORBIDDEN` — MFA not in setup state (code: `MFA_NOT_PENDING`)

---

### 2.7 POST `/auth/mfa/disable`

**Auth:** Access token
**Permission:** `auth.mfa.manage` (self)
**Description:** Disable MFA with password confirmation.

**Request:**

```json
{ "password": "currentPassword123" }
```

**Response 200:**

```json
{ "message": "MFA disabled successfully", "mfa_enabled": false }
```

**Errors:**

- `400 BAD_REQUEST` — Incorrect password (code: `INVALID_PASSWORD`)
- `403 FORBIDDEN` — MFA not enabled (code: `MFA_NOT_ENABLED`)

---

### 2.8 POST `/auth/mfa/challenge`

**Auth:** MFA token (from login response, Bearer)
**Rate Limit:** IP: 10/min, User: 20/min
**Description:** Verify TOTP during login flow to get full tokens.

**Request:**

```json
{ "code": "123456" }
```

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { ... }
}
```

*Refresh token set in cookie.*

**Errors:**

- `401 UNAUTHORIZED` — Invalid/expired MFA token (code: `INVALID_MFA_TOKEN`)
- `400 BAD_REQUEST` — Invalid TOTP code (code: `INVALID_TOTP_CODE`)
- `429 TOO_MANY_REQUESTS` — Rate limited (code: `RATE_LIMITED`)

---

## 3. Users Module

### 3.1 GET `/users/me`

**Auth:** Access token
**Description:** Current user profile + resolved permissions for active tenant.

**Response 200:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "full_name": "Juan Pérez",
  "avatar_url": null,
  "is_active": true,
  "mfa_enabled": true,
  "last_login_at": "2025-01-15T10:30:00Z",
  "created_at": "2025-01-10T08:00:00Z",
  "permissions": ["organization.read", "user.read", "user.update", "membership.read", "audit.read", ...],
  "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
  "tenant_name": "Conjunto Residencial Los Pinos",
  "active_membership": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "organization_id": "660e8400-e29b-41d4-a716-446655440001",
    "property_id": null,
    "role": "org_admin",
    "is_active": true
  }
}
```

---

### 3.2 PATCH `/users/me`

**Auth:** Access token
**Permission:** `user.update` (self)
**Description:** Update own profile (name, avatar). Cannot change email, roles, tenant.

**Request:**

```json
{ "full_name": "Juan Carlos Pérez", "avatar_url": "https://cdn.example.com/avatar.png" }
```

**Response 200:** Updated user object (same shape as GET `/users/me`)

**Errors:**

- `403 FORBIDDEN` — Attempted to modify restricted field (code: `FIELD_NOT_ALLOWED`)

---

### 3.3 POST `/users/me/password`

**Auth:** Access token
**Permission:** `user.password.change` (self)
**Description:** Change own password.

**Request:**

```json
{ "current_password": "oldPassword123", "new_password": "newSecurePassword456" }
```

**Response 200:**

```json
{ "message": "Password changed successfully" }
```

**Errors:**

- `400 BAD_REQUEST` — Current password incorrect (code: `INVALID_CURRENT_PASSWORD`)
- `422 VALIDATION_ERROR` — New password fails policy (code: `WEAK_PASSWORD`)

---

### 3.4 GET `/users/me/sessions`

**Auth:** Access token
**Permission:** `user.session.read` (self)
**Description:** List all active sessions across devices.

**Response 200:**

```json
{
  "items": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
      "ip": "192.168.1.100",
      "last_activity_at": "2025-01-15T10:25:00Z",
      "created_at": "2025-01-15T08:00:00Z",
      "is_current": true
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

---

### 3.5 DELETE `/users/me/sessions/{session_id}`

**Auth:** Access token
**Permission:** `user.session.revoke` (self)
**Description:** Revoke specific session.

**Response 200:**

```json
{ "message": "Session revoked" }
```

**Errors:**

- `404 NOT_FOUND` — Session not found or not owned by user (code: `SESSION_NOT_FOUND`)

---

### 3.6 GET `/users`

**Auth:** Access token
**Permission:** `user.read`
**Description:** List users in current tenant (paginated, filterable).

**Query Params:** `page`, `page_size`, `search` (email/name), `is_active`, `role`

**Response 200:** Paginated user list (subset of `/users/me` fields)

---

### 3.7 GET `/users/{user_id}`

**Auth:** Access token
**Permission:** `user.read`
**Description:** Get single user in current tenant.

**Response 200:** User object (same as list item)

**Errors:**

- `404 NOT_FOUND` — User not found in current tenant (code: `USER_NOT_FOUND`)

---

### 3.8 PATCH `/users/{user_id}`

**Auth:** Access token
**Permission:** `user.update`
**Description:** Admin update user in current tenant.

**Request:**

```json
{ "full_name": "New Name", "is_active": false }
```

**Response 200:** Updated user object

**Errors:**

- `404 NOT_FOUND` — User not in current tenant (code: `USER_NOT_FOUND`)
- `403 FORBIDDEN` — Cannot modify super-admin (code: `SUPER_ADMIN_IMMUTABLE`)

---

### 3.9 DELETE `/users/{user_id}`

**Auth:** Access token
**Permission:** `user.delete`
**Description:** Soft-delete user in current tenant.

**Response 200:**

```json
{ "message": "User deleted", "deleted_at": "2025-01-15T10:30:00Z" }
```

**Errors:**

- `404 NOT_FOUND` — User not in current tenant (code: `USER_NOT_FOUND`)
- `403 FORBIDDEN` — Cannot delete self or super-admin (code: `DELETE_NOT_ALLOWED`)

---

### 3.10 GET `/users/me/mfa`

**Auth:** Access token
**Permission:** `auth.mfa.manage` (self)
**Description:** List enrolled MFA devices.

**Response 200:**

```json
{
  "items": [
    { "id": "990e8400-e29b-41d4-a716-446655440004", "name": "Authenticator App", "is_primary": true, "last_used_at": "2025-01-15T10:00:00Z", "created_at": "2025-01-10T08:00:00Z" }
  ]
}
```

---

### 3.11 DELETE `/users/me/mfa/{device_id}`

**Auth:** Access token
**Permission:** `auth.mfa.manage` (self)
**Description:** Remove MFA device (requires password confirmation via header or body).

**Request:**

```json
{ "password": "currentPassword123" }
```

**Response 200:**

```json
{ "message": "MFA device removed" }
```

**Errors:**

- `400 BAD_REQUEST` — Incorrect password (code: `INVALID_PASSWORD`)
- `404 NOT_FOUND` — Device not found (code: `MFA_DEVICE_NOT_FOUND`)

---

## 4. Organizations Module

### 4.1 POST `/organizations`

**Auth:** Access token
**Permission:** `organization.create` (Super Admin only)
**Description:** Create new organization (additional org beyond self-service).

**Request:**

```json
{ "name": "Nueva Organización", "slug": "nueva-org", "description": "Descripción" }
```

**Response 201:** Organization object

**Errors:**

- `403 FORBIDDEN` — Not super-admin (code: `SUPER_ADMIN_REQUIRED`)
- `409 CONFLICT` — Slug exists (code: `SLUG_EXISTS`)

---

### 4.2 GET `/organizations/me`

**Auth:** Access token
**Permission:** `organization.read`
**Description:** Current user's organization.

**Response 200:**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "Conjunto Residencial Los Pinos",
  "slug": "los-pinos",
  "description": "Conjunto residencial en Bogotá",
  "settings": {},
  "created_at": "2025-01-10T08:00:00Z",
  "updated_at": "2025-01-10T08:00:00Z"
}
```

---

### 4.3 PATCH `/organizations/me`

**Auth:** Access token
**Permission:** `organization.update`
**Description:** Update organization settings.

**Request:**

```json
{ "name": "Nuevo Nombre", "description": "Nueva descripción", "settings": { "timezone": "America/Bogota" } }
```

**Response 200:** Updated organization object

---

### 4.4 GET `/organizations/me/properties`

**Auth:** Access token
**Permission:** `property.read`
**Description:** List properties/groups in current organization.

**Response 200:** Paginated property list

---

### 4.5 POST `/organizations/me/properties`

**Auth:** Access token
**Permission:** `property.create`
**Description:** Create property/group.

**Request:**

```json
{ "name": "Torre A", "code": "TORRE-A", "description": "Torre principal" }
```

**Response 201:** Property object

**Errors:**

- `409 CONFLICT` — Code exists in organization (code: `PROPERTY_CODE_EXISTS`)

---

### 4.6 PATCH `/organizations/me/properties/{property_id}`

**Auth:** Access token
**Permission:** `property.update`
**Description:** Update property.

**Response 200:** Updated property

**Errors:**

- `404 NOT_FOUND` — Property not in current tenant (code: `PROPERTY_NOT_FOUND`)

---

### 4.7 DELETE `/organizations/me/properties/{property_id}`

**Auth:** Access token
**Permission:** `property.delete`
**Description:** Delete property (sets memberships.property_id = NULL).

**Response 200:**

```json
{ "message": "Property deleted" }
```

**Errors:**

- `404 NOT_FOUND` — Property not in current tenant (code: `PROPERTY_NOT_FOUND`)

---

### 4.8 GET `/organizations/me/memberships`

**Auth:** Access token
**Permission:** `membership.read`
**Description:** List memberships in current organization.

**Response 200:** Paginated membership list with user + role details

---

### 4.9 POST `/organizations/me/memberships`

**Auth:** Access token
**Permission:** `membership.create`
**Description:** Add member to organization.

**Request:**

```json
{ "user_id": "550e8400-e29b-41d4-a716-446655440005", "role": "resident", "property_id": "770e8400-e29b-41d4-a716-446655440006" }
```

**Response 201:** Membership object

**Errors:**

- `404 NOT_FOUND` — User not found or property not in tenant (code: `USER_NOT_FOUND`, `PROPERTY_NOT_FOUND`)
- `409 CONFLICT` — User already member of this organization (code: `MEMBERSHIP_EXISTS`)

---

### 4.10 PATCH `/organizations/me/memberships/{membership_id}`

**Auth:** Access token
**Permission:** `membership.update`
**Description:** Update membership role/property.

**Request:**

```json
{ "role": "board_member", "property_id": "770e8400-e29b-41d4-a716-446655440006" }
```

**Response 200:** Updated membership

**Errors:**

- `404 NOT_FOUND` — Membership not in current tenant (code: `MEMBERSHIP_NOT_FOUND`)

---

### 4.11 DELETE `/organizations/me/memberships/{membership_id}`

**Auth:** Access token
**Permission:** `membership.delete`
**Description:** Remove member from organization.

**Response 200:**

```json
{ "message": "Member removed" }
```

**Errors:**

- `404 NOT_FOUND` — Membership not in current tenant (code: `MEMBERSHIP_NOT_FOUND`)
- `403 FORBIDDEN` — Cannot remove self/last admin (code: `REMOVE_NOT_ALLOWED`)

---

## 5. RBAC Module

### 5.1 GET `/rbac/permissions`

**Auth:** Access token
**Permission:** `permission.read`
**Description:** List all permissions (global registry).

**Response 200:**

```json
{
  "items": [
    { "id": "perm-uuid", "name": "meeting.create", "resource": "meeting", "action": "create", "description": "Create meetings", "is_system": true }
  ],
  "total": 35,
  "page": 1,
  "page_size": 20,
  "pages": 2
}
```

---

### 5.2 GET `/rbac/roles`

**Auth:** Access token
**Permission:** `role.read`
**Description:** List roles in current tenant (base + custom).

**Response 200:** Paginated role list

---

### 5.3 POST `/rbac/roles`

**Auth:** Access token
**Permission:** `role.create`
**Description:** Create custom role in current tenant.

**Request:**

```json
{ "name": "custom_manager", "display_name": "Custom Manager", "description": "Manager with limited perms", "permission_ids": ["perm-uuid-1", "perm-uuid-2"] }
```

**Response 201:** Created role with permissions

**Errors:**

- `403 FORBIDDEN` — Attempt to create system role name (code: `SYSTEM_ROLE_NAME_RESERVED`)
- `409 CONFLICT` — Role name exists in tenant (code: `ROLE_NAME_EXISTS`)

---

### 5.4 PATCH `/rbac/roles/{role_id}`

**Auth:** Access token
**Permission:** `role.update`
**Description:** Update custom role (name, permissions). Cannot modify system roles.

**Request:**

```json
{ "display_name": "New Name", "permission_ids": ["perm-uuid-1", "perm-uuid-3"] }
```

**Response 200:** Updated role

**Errors:**

- `404 NOT_FOUND` — Role not in current tenant (code: `ROLE_NOT_FOUND`)
- `403 FORBIDDEN` — Cannot modify system role (code: `SYSTEM_ROLE_IMMUTABLE`)

---

### 5.5 DELETE `/rbac/roles/{role_id}`

**Auth:** Access token
**Permission:** `role.delete`
**Description:** Delete custom role. Cannot delete system roles or roles with assigned users.

**Response 200:**

```json
{ "message": "Role deleted" }
```

**Errors:**

- `404 NOT_FOUND` — Role not in current tenant (code: `ROLE_NOT_FOUND`)
- `403 FORBIDDEN` — System role or has assigned users (code: `ROLE_CANNOT_DELETE`)

---

### 5.6 POST `/rbac/roles/{role_id}/permissions`

**Auth:** Access token
**Permission:** `role.permission.assign`
**Description:** Assign permission to role.

**Request:**

```json
{ "permission_id": "perm-uuid" }
```

**Response 200:** Updated role with permissions

**Errors:**

- `404 NOT_FOUND` — Role or permission not found (code: `ROLE_NOT_FOUND`, `PERMISSION_NOT_FOUND`)

---

### 5.7 DELETE `/rbac/roles/{role_id}/permissions/{permission_id}`

**Auth:** Access token
**Permission:** `role.permission.revoke`
**Description:** Revoke permission from role.

**Response 200:**

```json
{ "message": "Permission revoked from role" }
```

**Errors:**

- `404 NOT_FOUND` — Assignment not found (code: `ROLE_PERMISSION_NOT_FOUND`)

---

### 5.8 POST `/rbac/users/{user_id}/roles`

**Auth:** Access token
**Permission:** `user.role.assign`
**Description:** Assign role to user in current tenant.

**Request:**

```json
{ "role_id": "role-uuid" }
```

**Response 200:**

```json
{ "message": "Role assigned", "user_role": { "user_id": "...", "role_id": "...", "organization_id": "...", "created_at": "..." } }
```

**Errors:**

- `404 NOT_FOUND` — User not in tenant or role not in tenant (code: `USER_NOT_FOUND`, `ROLE_NOT_FOUND`)
- `409 CONFLICT` — Assignment already exists (code: `ROLE_ASSIGNMENT_EXISTS`)

---

### 5.9 DELETE `/rbac/users/{user_id}/roles/{role_id}`

**Auth:** Access token
**Permission:** `user.role.revoke`
**Description:** Revoke role from user in current tenant.

**Response 200:**

```json
{ "message": "Role revoked from user" }
```

**Errors:**

- `404 NOT_FOUND` — Assignment not found (code: `USER_ROLE_NOT_FOUND`)
- `403 FORBIDDEN` — Cannot revoke org_admin from last admin (code: `LAST_ADMIN_PROTECTED`)

---

## 6. Audit Module

### 6.1 GET `/audit`

**Auth:** Access token
**Permission:** `audit.read`
**Description:** Paginated, filterable audit log for current tenant.

**Query Params:**

- `page`, `page_size`
- `action` (exact match)
- `resource` (exact match)
- `resource_id` (UUID)
- `actor_user_id` (UUID)
- `date_from`, `date_to` (ISO 8601)
- `ip` (INET)

**Response 200:**

```json
{
  "items": [
    {
      "id": "audit-uuid",
      "actor_user_id": "550e8400-e29b-41d4-a716-446655440000",
      "actor_email": "admin@example.com",
      "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
      "action": "user.create",
      "resource": "user",
      "resource_id": "550e8400-e29b-41d4-a716-446655440005",
      "timestamp": "2025-01-15T10:30:00Z",
      "ip": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "metadata": { "source": "api", "details": {} }
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

---

### 6.2 GET `/audit/{audit_id}`

**Auth:** Access token
**Permission:** `audit.read`
**Description:** Single audit event detail.

**Response 200:** Audit event object (same as list item)

**Errors:**

- `404 NOT_FOUND` — Event not in current tenant (code: `AUDIT_EVENT_NOT_FOUND`)

---

## 7. Error Code Reference

| HTTP | Code | Description |
| ------ | ------ | ------------- |
| 400 | `INVALID_TOTP_CODE` | TOTP code incorrect |
| 400 | `INVALID_PASSWORD` | Password incorrect |
| 400 | `INVALID_CURRENT_PASSWORD` | Current password incorrect |
| 400 | `WEAK_PASSWORD` | New password fails policy |
| 400 | `INVALID_MFA_TOKEN` | MFA challenge token invalid/expired |
| 400 | `MFA_NOT_PENDING` | MFA not in setup state |
| 400 | `MFA_NOT_ENABLED` | MFA not enabled for user |
| 401 | `INVALID_CREDENTIALS` | Email/password incorrect |
| 401 | `INVALID_TOKEN` | Access token invalid/expired/malformed |
| 401 | `INVALID_REFRESH_TOKEN` | Refresh token invalid/expired/revoked |
| 401 | `REFRESH_TOKEN_REUSE_DETECTED` | Reuse detected, chain revoked |
| 403 | `USER_INACTIVE` | User soft-deleted or inactive |
| 403 | `MFA_REQUIRED_FOR_ROLE` | Admin role requires MFA |
| 403 | `MFA_ALREADY_ENABLED` | MFA already enabled |
| 403 | `SUPER_ADMIN_REQUIRED` | Super Admin permission required |
| 403 | `SUPER_ADMIN_IMMUTABLE` | Cannot modify Super Admin |
| 403 | `SYSTEM_ROLE_IMMUTABLE` | Cannot modify system role |
| 403 | `SYSTEM_ROLE_NAME_RESERVED` | Cannot use system role name |
| 403 | `ROLE_CANNOT_DELETE` | System role or has assigned users |
| 403 | `DELETE_NOT_ALLOWED` | Cannot delete self or super-admin |
| 403 | `REMOVE_NOT_ALLOWED` | Cannot remove self/last admin |
| 403 | `LAST_ADMIN_PROTECTED` | Cannot revoke last admin role |
| 403 | `FIELD_NOT_ALLOWED` | Cannot modify restricted field |
| 404 | `USER_NOT_FOUND` | User not in tenant |
| 404 | `PROPERTY_NOT_FOUND` | Property not in tenant |
| 404 | `MEMBERSHIP_NOT_FOUND` | Membership not in tenant |
| 404 | `ROLE_NOT_FOUND` | Role not in tenant |
| 404 | `SESSION_NOT_FOUND` | Session not owned by user |
| 404 | `MFA_DEVICE_NOT_FOUND` | MFA device not found |
| 404 | `AUDIT_EVENT_NOT_FOUND` | Audit event not in tenant |
| 409 | `EMAIL_EXISTS` | Email already registered |
| 409 | `SLUG_EXISTS` | Organization slug exists |
| 409 | `PROPERTY_CODE_EXISTS` | Property code exists in org |
| 409 | `MEMBERSHIP_EXISTS` | User already member of org |
| 409 | `ROLE_NAME_EXISTS` | Role name exists in tenant |
| 409 | `ROLE_ASSIGNMENT_EXISTS` | User already has role |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 429 | `RATE_LIMITED` | Rate limit exceeded |

---

## 8. OpenAPI Generation

FastAPI auto-generates `/openapi.json` and `/docs` (Swagger UI) from route signatures and Pydantic models. All schemas defined in module `schemas.py` files. The contract above is the source of truth; implementation must match.
