# API Contract: meetings-crud

**Change ID:** `meetings-crud`
**Status:** Design
**Date:** 2025-01-20
**Base Path:** `/api/v1`
**Parent Change:** `auth-multitenant-foundation`

---

## 1. Conventions (inherit from api-contract.md §1)

- **Authentication:** Bearer token (JWT access token) unless noted.
- **Tenant Scoping:** Automatic via `tenant_id` from authenticated user's active membership. Never passed by client.
- **Permissions:** Enforced via `require_permission("resource.action")` dependency. Returns 401 (unauthenticated), 403 (unauthorized/forbidden), 404 (cross-tenant/resource not found), 422 (validation/invalid state), 409 (conflict).
- **Pagination:** `?page=1&page_size=20` (max 100). Response:

  ```json
  { "items": [], "total": 0, "page": 1, "page_size": 20, "pages": 1 }
  ```

- **Timestamps:** ISO 8601 UTC (`2025-01-20T14:30:00Z`) in responses. Input accepts ISO 8601 with offset; America/Bogota conversion at edges.
- **UUIDs:** Lowercase with hyphens (`550e8400-e29b-41d4-a716-446655440000`).
- **Error format:** `{ "detail": "Human-readable message", "code": "ERROR_CODE", "meta": {} }`

---

## 2. Error Code Reference (meetings-crud)

| HTTP | Code | Description |
| ------ | ------ | ------------- |
| 401 | `INVALID_TOKEN` | Access token invalid/expired/malformed |
| 401 | `REFRESH_TOKEN_REUSE_DETECTED` | (inherited from auth; not meetings-specific) |
| 403 | `PERMISSION_DENIED` | User lacks `meeting.read/create/update/cancel/participant_manage` |
| 403 | `TENANT_ISOLATION_VIOLATION` | (cross-tenant access attempt — treated as 404 per policy) |
| 404 | `MEETING_NOT_FOUND` | Meeting not found in current tenant (cross-tenant → 404, never 403) |
| 404 | `PARTICIPANT_NOT_FOUND` | Participant not found in current tenant |
| 409 | `MEETING_DUPLICATE_TITLE` | (optional: title must be unique per tenant — see data-model; if enforced, 409) |
| 409 | `MEETING_DUPLICATE_PARTICIPANT` | Internal user already participant or email already invited to same meeting |
| 422 | `MEETING_INVALID_STATUS_TRANSITION` | Status PATCH with non-allowed transition |
| 422 | `MEETING_VALIDATION_ERROR` | Request body validation failed (Pydantic) |
| 429 | `RATE_LIMITED` | (inherited from auth; applies to create/list endpoints) |

**Cross-tenant policy:** Every meeting or participant query/mutation from a token belonging to Tenant A against a resource of Tenant B returns **404** (`MEETING_NOT_FOUND` / `PARTICIPANT_NOT_FOUND`), **never 403**. This prevents leaking existence of meetings across tenants.

---

## 3. Module: `/meetings` (CRUD + Participants)

### 3.1 POST `/api/v1/meetings`

**Auth:** Access token
**Permission:** `meeting.create`
**Description:** Create a new meeting. Tenant is auto-resolved from user's active membership.

**Request:**

```json
{
  "title": "Construcción de muro de contención",
  "description": "Reunión de seguimiento de obra",
  "scheduled_at": "2025-03-15T09:00:00-05:00",  // America/Bogota local with offset
  "start_at": "2025-03-15T09:30:00-05:00",
  "end_at": "2025-03-15T11:00:00-05:00",
  "location": "Sala de juntas, Torre A",
  "modality": "in_person"
}
```

**Response 201:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Construcción de muro de contención",
  "description": "Reunión de seguimiento de obra",
  "scheduled_at": "2025-03-15T14:30:00Z",  // UTC in response
  "start_at": "2025-03-15T14:30:00Z",
  "end_at": "2025-03-15T16:00:00Z",
  "location": "Sala de juntas, Torre A",
  "modality": "in_person",
  "status": "scheduled",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
  "created_at": "2025-01-20T18:45:00Z",
  "updated_at": "2025-01-20T18:45:00Z"
}
```

**Errors:**

- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)
- `403 FORBIDDEN` — User lacks `meeting.create` (code: `PERMISSION_DENIED`)
- `422 VALIDATION_ERROR` — Invalid input format (code: `MEETING_VALIDATION_ERROR`), e.g. `start_at` after `end_at`, `scheduled_at` before now, `modality` not in enum

---

### 3.2 GET `/api/v1/meetings`

**Auth:** Access token
**Permission:** `meeting.read`
**Description:** List meetings for the authenticated tenant. Paginated and filterable.

**Query Params:**

| Param | Type | Description |
| ------ | ----- | ------------ |
| `page` | int (default: 1) | Page number |
| `page_size` | int (default: 20, max: 100) | Items per page |
| `status` | VARCHAR | Filter by status (`scheduled`, `in_progress`, `finished`, `cancelled`) |
| `date_from` | TIMESTAMPTZ | Filter: `scheduled_at >= date_from` |
| `date_to` | TIMESTAMPTZ | Filter: `scheduled_at <= date_to` |
| `q` | VARCHAR | Substring search on `title` (case-insensitive) |

**Response 200:**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Construcción de muro de contención",
      "status": "scheduled",
      "scheduled_at": "2025-03-15T14:30:00Z",
      "modality": "in_person",
      "tenant_id": "660e8400-e29b-41d4-a716-446655440001"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

**Errors:**

- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)
- `403 FORBIDDEN` — User lacks `meeting.read` (code: `PERMISSION_DENIED`)

---

### 3.3 GET `/api/v1/meetings/{meeting_id}`

**Auth:** Access token
**Permission:** `meeting.read`
**Description:** Get a single meeting. Cross-tenant → 404 (`MEETING_NOT_FOUND`).

**Response 200:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Construcción de muro de contención",
  "description": "Reunión de seguimiento de obra",
  "scheduled_at": "2025-03-15T14:30:00Z",
  "start_at": "2025-03-15T14:30:00Z",
  "end_at": "2025-03-15T16:00:00Z",
  "location": "Sala de juntas, Torre A",
  "modality": "in_person",
  "status": "scheduled",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
  "created_at": "2025-01-20T18:45:00Z",
  "updated_at": "2025-01-20T18:55:00Z"
}
```

**Errors:**

- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)
- `403 FORBIDDEN` — User lacks `meeting.read` (code: `PERMISSION_DENIED`) — **in-tenant without permission**
- `404 NOT_FOUND` — Meeting not in current tenant (code: `MEETING_NOT_FOUND`) — **cross-tenant** (the critical IDOR prevention)

---

### 3.4 PATCH `/api/v1/meetings/{meeting_id}`

**Auth:** Access token
**Permission:** `meeting.update`
**Description:** Update meeting fields. Status transitions validated via FSM; same status is idempotent (no-op, no audit event).

**Request:**

```json
{
  "status": "in_progress"
}
```

Only `status` is allowed in the PATCH body for status changes; other fields (`title`, `description`, `location`, `modality`) can also be PATCHed but are not the focus of this contract section.

**Response 200:** Updated meeting object (same shape as GET detail).

**Errors:**

- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)
- `403 FORBIDDEN` — User lacks `meeting.update` (code: `PERMISSION_DENIED`)
- `422 VALIDATION_ERROR` — Invalid field values (code: `MEETING_VALIDATION_ERROR`), e.g. `start_at >= end_at`
- `422 MEETING_INVALID_STATUS_TRANSITION` — Status transition not allowed by FSM (code: `MEETING_INVALID_STATUS_TRANSITION`)

**FSM Transition Table (documented for developers):**

| From → To | Allowed? | Error Code if Disallowed |
| --------- | -------- | ------------------------ |
| `scheduled` → `in_progress` | ✅ | `MEETING_INVALID_STATUS_TRANSITION` |
| `scheduled` → `finished` | ❌ | `MEETING_INVALID_STATUS_TRANSITION` |
| `scheduled` → `cancelled` | ✅ | `MEETING_INVALID_STATUS_TRANSITION` |
| `in_progress` → `finished` | ✅ | `MEETING_INVALID_STATUS_TRANSITION` |
| `in_progress` → `cancelled` | ✅ | `MEETING_INVALID_STATUS_TRANSITION` |
| `finished` → any | ❌ | N/A (terminal) |
| `cancelled` → any | ❌ | N/A (terminal) |
| Same status → | ✅ | Idempotent, no-op, no audit event |

---

### 3.5 POST `/api/v1/meetings/{meeting_id}/cancel`

**Auth:** Access token
**Permission:** `meeting.cancel`
**Description:** Cancel a meeting (set status to `cancelled`). Allowed from any non-terminal state.

**Request:** Empty body (no fields needed; status is implied)

**Response 200:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Meeting cancelled successfully"
}
```

**Errors:**

- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)
- `403 FORBIDDEN` — User lacks `meeting.cancel` (code: `PERMISSION_DENIED`)
- `404 NOT_FOUND` — Meeting not in current tenant (code: `MEETING_NOT_FOUND`)
- `422 MEETING_INVALID_STATUS_TRANSITION` — Meeting already `finished` (cannot cancel terminal state)

---

### 3.6 POST `/api/v1/meetings/{meeting_id}/participants`

**Auth:** Access token
**Permission:** `meeting.participant_manage`
**Description:** Add a participant to the meeting. Internal user (by `user_id`) or external invitee (by `email`).

**Request — Internal user:**

```json
{ "user_id": "550e8400-e29b-41d4-a716-446655440005" }
```

**Request — External invitee:**

```json
{ "email": "invitado@ejemplo.com" }
```

**Response 201 (internal user):**

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440005",
  "meeting_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440005",
  "email": null,
  "role": "organizer",
  "status": "active",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

**Response 201 (external invitee):**

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440005",
  "meeting_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": null,
  "email": "invitado@ejemplo.com",
  "role": "attendee",
  "status": "active",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

**Errors:**

- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)
- `403 FORBIDDEN` — User lacks `meeting.participant_manage` (code: `PERMISSION_DENIED`)
- `404 NOT_FOUND` — Meeting not in current tenant (code: `MEETING_NOT_FOUND`)
- `409 MEETING_DUPLICATE_PARTICIPANT` — Internal user already participant in this meeting (code: `MEETING_DUPLICATE_PARTICIPANT`), or external email already invited

---

### 3.7 DELETE `/api/v1/meetings/{meeting_id}/participants/{participant_id}`

**Auth:** Access token
**Permission:** `meeting.participant_manage`
**Description:** Remove a participant from the meeting.

**Response 204:** No content (204 No Content).

**Errors:**

- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)
- `403 FORBIDDEN` — User lacks `meeting.participant_manage` (code: `PERMISSION_DENIED`)
- `404 NOT_FOUND` — Meeting not in current tenant (code: `MEETING_NOT_FOUND`), or participant not found in current tenant (code: `PARTICIPANT_NOT_FOUND`)

---

### 3.8 GET `/api/v1/meetings/{meeting_id}/participants`

**Auth:** Access token
**Permission:** `meeting.read`
**Description:** List participants for a meeting. Cross-tenant → 404.

**Response 200:** Paginated list of participant objects (same shape as POST response above, without `id` perhaps, or with it).

**Errors:**

- `401 UNAUTHORIZED` — Invalid token (code: `INVALID_TOKEN`)
- `403 FORBIDDEN` — User lacks `meeting.read` (code: `PERMISSION_DENIED`) — in-tenant without permission
- `404 NOT_FOUND` — Meeting not in current tenant (code: `MEETING_NOT_FOUND`) — cross-tenant

---

## 4. Request/Response Schemas (Pydantic conventions, matching api-contract.md §2 style)

### 4.1 MeetingCreate

```python
class MeetingCreate(BaseModel):
    title: str  # max 255 chars
    description: str | None = None
    scheduled_at: datetime  # ISO 8601 with offset; server converts America/Bogota → UTC
    start_at: datetime  # ISO 8601 with offset
    end_at: datetime  # ISO 8601 with offset
    location: str | None = None  # max 500 chars
    modality: str  # 'in_person' | 'virtual' | 'hybrid'
```

### 4.2 MeetingResponse

```python
class MeetingResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    scheduled_at: datetime  # UTC ISO 8601 (output, always ends with Z)
    start_at: datetime  # UTC ISO 8601
    end_at: datetime  # UTC ISO 8601
    location: str | None = None
    modality: str  # 'in_person' | 'virtual' | 'hybrid'
    status: str  # 'scheduled' | 'in_progress' | 'finished' | 'cancelled'
    tenant_id: uuid.UUID
    created_at: datetime  # UTC ISO 8601
    updated_at: datetime  # UTC ISO 8601
```

### 4.3 MeetingUpdate (PATCH)

```python
class MeetingUpdate(BaseModel):
    status: str | None = None  # If provided, validated via FSM
    title: str | None = None
    description: str | None = None
    location: str | None = None
    modality: str | None = None
```

### 4.4 ParticipantCreate

```python
class ParticipantCreate(BaseModel):
    user_id: uuid.UUID | None = None  # Internal user; one of user_id/email must be set
    email: str | None = None  # External invitee; one of user_id/email must be set
    role: str | None = None  # 'organizer' | 'presenter' | 'attendee'; defaults to 'attendee'
```

### 4.5 ParticipantResponse

```python
class ParticipantResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    user_id: uuid.UUID | None = None
    email: str | None = None
    role: str  # 'organizer' | 'presenter' | 'attendee'
    status: str  # 'active' | 'removed'
    created_at: datetime  # UTC ISO 8601
```

---

## 5. RBAC Permission Names (meetings-crud)

| Permission | Description | Base roles initially granted |
| ---------- | ------------ | ---------------------------- |
| `meeting.create` | Create meetings | org_admin, president, secretary (see auth foundation matrix) |
| `meeting.read` | Read meetings (list + detail) | All roles; cross-tenant → 404 |
| `meeting.update` | Update meetings (status, fields) | org_admin, president, secretary |
| `meeting.cancel` | Cancel meetings (set status cancelled) | org_admin, president, secretary |
| `meeting.participant_manage` | Manage participants (add/remove) | org_admin, president, secretary |

**Note:** Resident and guest roles have `meeting.read` only (read-own, per auth foundation §5.2 matrix). Board member may have `meeting.read` only.

---

## 6. Open Questions

- [ ] None. All decisions traced to proposal, specs, and foundation conventions.