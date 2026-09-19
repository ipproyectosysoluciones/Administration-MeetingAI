# Architecture Design: meetings-crud

**Change ID:** `meetings-crud`
**Status:** Design
**Date:** 2025-01-20

---

## 1. Context & Decisions Summary

This document records the architectural decisions for the meetings CRUD module. All decisions trace to the proposal (`proposal.md`), specs (`specs/meetings/spec.md`), and the foundation change (`auth-multitenant-foundation`). Trade-offs are noted inline per openspec rules.

The meetings module is the entry point of every downstream artifact: recording uploads, transcription jobs, minutes drafts, and approvals all hang from a meeting entity.

---

## 2. Module Layout & Dependency Graph

### 2.1 Directory Structure

```
app/
├── core/                          # Shared infrastructure (no module deps)
│   ├── config.py                  # Pydantic Settings, .env loading
│   ├── security.py                # JWT (RS256), Argon2id, token utilities
│   ├── database.py                # SQLAlchemy engine, session, declarative base
│   ├── exceptions.py              # Domain exceptions (AuthError, TenantError, ...)
│   ├── middleware/
│   │   ├── tenant_context.py      # TenantContextMiddleware, get_tenant_id() dep
│   │   ├── audit_middleware.py    # Auto-audit for mutating endpoints
│   │   ├── rate_limit.py          # In-memory rate limiter (no Redis)
│   │   └── security_headers.py    # CSP, HSTS, X-Frame-Options, Referrer-Policy
│   └── dependencies.py            # FastAPI deps: get_current_user, get_db, require_permission
├── modules/                       # Feature modules (acyclic deps only)
│   ├── auth/                      # (existing, from auth-multitenant-foundation)
│   ├── users/                     # (existing, from auth-multitenant-foundation)
│   ├── organizations/             # (existing, from auth-multitenant-foundation)
│   ├── rbac/                      # (existing, from auth-multitenant-foundation)
│   ├── audit/                     # (existing, from auth-multitenant-foundation)
│   └── meetings/                  # NEW — meetings CRUD + participants
│       ├── router.py              # CRUD + participant routes
│       ├── service.py             # Business logic, status FSM, participant mgmt
│       ├── schemas.py             # Pydantic request/response models
│       ├── repository.py          # Data access for Meeting, MeetingParticipant
│       └── models.py              # SQLAlchemy models
├── main.py                        # FastAPI app factory, router inclusion
└── cli/
    └── bootstrap_superadmin.py    # Idempotent Super Admin creation script
```

### 2.2 Module Dependency Graph (Acyclic)

```
core (no deps)
    ↑
    ├── auth          → depends on: core, users, rbac, audit
    ├── users         → depends on: core, organizations, rbac, audit
    ├── organizations → depends on: core, users, rbac, audit
    ├── rbac          → depends on: core, organizations, audit
    ├── audit         → depends on: core (only)
    └── meetings      → depends on: core, organizations, rbac, audit (only)
```

**Critical invariant:** No module imports another module's router or service directly. Cross-module calls go through `core.dependencies` (e.g., `require_permission`) or explicit service imports that respect the DAG above.

**Meetings module boundaries:**
- **Reads:** `core.database`, `core.dependencies` (get_tenant_id, require_permission)
- **Writes:** `core.database`, `core.audit` (via service), own repository
- **Never imports:** `auth`, `users` modules directly. Calls tenant-scoped user operations through `core.dependencies` only.

---

## 2.3 Tenant Context & Scoping

### 2.3.1 Resolution Chain

```
Request
  → AuthMiddleware (validates JWT, extracts user_id)
  → TenantContextMiddleware
      → calls UserRepository.get_active_membership(user_id)
      → resolves membership.organization_id as tenant_id
      → stores in request.state.tenant_id
  → Route handler
      → repositories use get_tenant_id() dependency
      → all queries filter by tenant_id
```

### 2.3.2 Key Implementation Points

- **`get_tenant_id()` dependency** (in `core/dependencies.py`): Single source of truth. Raises `TenantError` if no active membership.
- **`TenantScopedRepository` base class**: All tenant-scoped repositories inherit; `query()` method auto-injects `.filter(tenant_id=get_tenant_id())`.
- **Never trust client `tenant_id`**: No endpoint accepts `tenant_id` as parameter; derived solely from membership.

---

## 2.4 Timezone Design

### 2.4.1 Storage Pattern

- **DB column:** `scheduled_at` TIMESTAMPTZ, `start_at` TIMESTAMPTZ, `end_at` TIMESTAMPTZ — **always stored as UTC**.
- **Input:** ISO 8601 with offset, accepted at API edges (POST/PATCH body). Client sends `America/Bogota` local time with `+00:00` or `America/Bogota` offset; server converts to UTC before storing.
- **Output:** ISO 8601 UTC in API responses (e.g., `2025-01-20T14:30:00Z`). Client formats to `America/Bogota` for display.

### 2.4.2 Edge Convertors

- **Input converter (fastapi dependency or Pydantic validator):** Parses incoming ISO string, detects `America/Bogota` intent, converts to `datetime.now(UTC)` for DB storage.
- **Output formatter (Pydantic model `model_dump` or `jsonable_encoder`):** Converts UTC `datetime` to ISO 8601 string with `Z` suffix.

### 2.4.3 Rationale

- **Storage:** Store once, convert anywhere. Avoids timezone ambiguity, DST transitions, and cross-regional comparison bugs.
- **Display:** Frontend (`America/Bogota`) renders the converted UTC value. No wall-clock strings ever hit the database.
- **Audit:** All timestamps stored UTC; audit events (`audit_events.timestamp`) also UTC.

**Decision:** Store UTC in DB, convert at edges. Never store wall-clock strings in DB.

---

## 3. Tables

### 3.1 `meetings`

| Column | Type | Nullable | Default | Description |
| -------- | ------ | -------- | -------- | ------------ |
| `id` | UUID | NO | `gen_random_uuid()` | PK, UUID v7 preferred, fallback `gen_random_uuid()` |
| `title` | VARCHAR(255) | NO | — | Meeting title |
| `description` | TEXT | YES | — | Optional description |
| `scheduled_at` | TIMESTAMPTZ | NO | — | UTC; input converted from America/Bogota local |
| `start_at` | TIMESTAMPTZ | NO | — | UTC; meeting start |
| `end_at` | TIMESTAMPTZ | NO | — | UTC; meeting end |
| `location` | VARCHAR(500) | YES | — | Physical or virtual link |
| `modality` | VARCHAR(20) | NO | `'in_person'` | `in_person` | `virtual` | `hybrid` |
| `status` | VARCHAR(20) | NO | `'scheduled'` | CHECK constraint: `scheduled` | `in_progress` | `finished` | `cancelled` |
| `tenant_id` | UUID | NO | — | FK → `organizations.id`; auto-resolved from membership |
| `deleted_at` | TIMESTAMPTZ | YES | NULL | Soft-delete; `deleted_at IS NULL` = active |
| `created_at` | TIMESTAMPTZ | NO | `now()` | Audit trail |
| `updated_at` | TIMESTAMPTZ | NO | `now()` | Audit trail |

**Indexes:**

| Index | Columns | Type |
| ------- | -------- | ------ |
| `ux_meetings_tenant_title` | `(tenant_id, title)` | Unique partial? No, just regular index for search |
| `ix_meetings_tenant_id` | `(tenant_id)` | Regular index, mandatory filter |
| `ix_meetings_tenant_status` | `(tenant_id, status)` | Compound for status-filtered list |
| `ix_meetings_scheduled_at` | `(scheduled_at)` | For timeline queries |
| `ix_meetings_deleted_at` | `(deleted_at)` | Where `deleted_at IS NOT NULL` |

**FKs:**

| Constraint | Reference | On Delete |
| ------------ | ---------- | ------------ |
| `meetings.tenant_id → organizations.id` | `organizations.id` | RESTRICT (protect meetings when org deleted) |

### 3.2 `meeting_participants`

| Column | Type | Nullable | Default | Description |
| -------- | ------ | -------- | -------- | ------------ |
| `id` | UUID | NO | `gen_random_uuid()` | PK |
| `meeting_id` | UUID | NO | — | FK → `meetings.id` |
| `tenant_id` | UUID | NO | — | FK → `organizations.id`; redundant for join efficiency; always equals `meeting.tenant_id` |
| `user_id` | UUID | YES | — | FK → `users.id` (internal participant). Null if external invitee only. |
| `email` | VARCHAR(255) | YES | — | External invitee email. Null if internal user (`user_id` set). |
| `role` | VARCHAR(20) | NO | `'attendee'` | CHECK constraint: `organizer` | `presenter` | `attendee` |
| `status` | VARCHAR(10) | NO | `'active'` | CHECK constraint: `active` | `removed` |
| `deleted_at` | TIMESTAMPTZ | YES | NULL | Soft-delete |
| `created_at` | TIMESTAMPTZ | NO | `now()` | Audit trail |

**Indexes:**

| Index | Columns | Type |
| ------- | -------- | ------ |
| `ix_meeting_participants_tenant_meeting` | `(tenant_id, meeting_id)` | Mandatory join index |
| `ix_meeting_participants_meeting_role` | `(meeting_id, role)` | For role-based queries |
| `ix_meeting_participants_tenant_date` | `(tenant_id, meeting_id)` | Covering index for tenant+meeting queries |
| `ix_meeting_participants_deleted_at` | `(deleted_at)` | Where `deleted_at IS NOT NULL` |

**Unique Constraints:**

| Constraint | Columns | Description |
| ------------ | -------- | ------------ |
| `uq_meeting_participants_tenant_user` | `(tenant_id, user_id)` WHERE `user_id IS NOT NULL` | One internal user per meeting (no duplicate user invites) |
| `uq_meeting_participants_tenant_email` | `(tenant_id, email)` WHERE `email IS NOT NULL` | One external invitee email per meeting (no duplicate emails) |
| `uq_meeting_participants_meeting_role_user` | `(meeting_id, user_id)` WHERE `user_id IS NOT NULL` | Ensures one role per user per meeting |
| `uq_meeting_participants_meeting_email` | `(meeting_id, email)` WHERE `email IS NOT NULL` | Ensures one email per meeting |

**FKs:**

| Constraint | Reference | On Delete |
| ------------ | ---------- | ------------ |
| `meeting_participants.meeting_id → meetings.id` | `meetings.id` | CASCADE (participants deleted when meeting deleted) |
| `meeting_participants.user_id → users.id` | `users.id` | RESTRICT (cannot delete user with active participants) |
| `meeting_participants.tenant_id → organizations.id` | `organizations.id` | RESTRICT |

**Check Constraints:**

```sql
CHECK (
    -- Exactly one of user_id or email is provided (internal or external, not both)
    (user_id IS NOT NULL AND email IS NULL) OR
    (user_id IS NULL AND email IS NOT NULL)
)
CHECK (
    role IN ('organizer', 'presenter', 'attendee')
)
CHECK (
    status IN ('active', 'removed')
)
```

---

## 4. Dependency Rules (Enforced)

| From → To | Reason |
| ----------|--------|
| `meetings → core` | Database engine, dependencies (get_tenant_id, require_permission) |
| `meetings → organizations` | `tenant_id` FK → `organizations.id`; read org name/slug for response |
| `meetings → rbac` | `require_permission("meeting.create/read/update/cancel/participant.manage")` |
| `meetings → audit` | Auto-audit middleware; explicit `AuditEvent` records on mutate |
| `meeting_participants → meetings` | FK `meeting_id`; cascade on meeting soft-delete |
| `meeting_participants → users` | FK `user_id`; restrict on user delete if participants exist |
| `meeting_participants → organizations` | `tenant_id` FK; consistent scoping |
| `meetings ↔ users` | Many-to-many via `meeting_participants`; no direct FK from users to meetings |
| **Never:** `meetings → auth`, `meetings ↔ users` (direct) | Cross-module via `core.dependencies` only |

**Critical invariant:** All meetings queries auto-inject `.filter(tenant_id=get_tenant_id())` via `TenantScopedRepository`. No endpoint accepts `tenant_id` from the client.

---

## 5. Status Lifecycle FSM

```
scheduled  ──(in_progress)──► in_progress ──(finished)──► finished
     │                                ▲
     └──(cancelled)──────────────────┘
```

**Transitions allowed:**

| From → To | Allowed? | Notes |
| --------- | -------- | --------|
| `scheduled` → `in_progress` | ✅ | Only if current time ≥ `scheduled_at` |
| `scheduled` → `finished` | ❌ | Must go through `in_progress` first |
| `scheduled` → `cancelled` | ✅ | From any non-terminal state |
| `in_progress` → `finished` | ✅ | |
| `in_progress` → `cancelled` | ✅ | |
| `finished` → any | ❌ | Terminal state |
| `cancelled` → any | ❌ | Terminal state (can only be viewed, not reverted) |

**Enforcement:** State machine in `meetings/service.py`; PATCH `/meetings/{id}` with `status` → 422 `INVALID_STATUS_TRANSITION` if not allowed. Same status → 200 idempotent (no-op, no audit event).

**Input/Output:** ISO 8601 UTC in API responses. Input accepts ISO 8601 with offset; server converts America/Bogota local → UTC before DB write.

---

## 6. Open Questions

- [ ] None. All decisions traced to proposal, specs, and foundation conventions.