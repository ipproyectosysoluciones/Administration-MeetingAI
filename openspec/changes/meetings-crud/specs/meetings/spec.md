# Specs — meetings module (delta)

## Permission namespace

New resource: `meeting` with actions below. Base roles extend per data-model §4 matrix (values marked ✓ also included in custom-role assignment pool).

| Permission | org_admin | secretary | president | board_member | resident |
|---|---|---|---|---|---|
| meeting.create | ✓ | ✓ | | | |
| meeting.read | ✓ | ✓ | ✓ | ✓ | read-own only |
| meeting.update | ✓ | ✓ | | | own* |
| meeting.cancel | ✓ | ✓ | | | |
| meeting.participant_manage | ✓ | ✓ | | | |

*overlapping edits of an attendance-marking allowed; see meeting_status rules.

## Requirements

### R1 — Meeting CRUD (tenant-scoped)
**Statement:** Tenant users with `meeting.create` can create meetings; only that tenant can read/update/cancel them.

**Scenarios:**
1. POST /meetings with valid fields → 201 with meeting; audit event recorded.
2. GET /meetings → 200 with only caller's tenant meetings; paginated, `page`, `page_size`; supports `?status`, `?date_from`, `?date_to`, `?q` (title substring).
3. GET /meetings/{id} cross-tenant → 404 (`MEETING_NOT_FOUND`); in-tenant without `meeting.read` → 403.
4. PATCH /meetings/{id} with `meeting.update` → 200 updated; status transitions only via state machine; audit event.
5. DELETE/cancel via POST /meetings/{id}/cancel with `meeting.cancel` → status `cancelled`, soft-delete-style (row stays; `status`+`deleted_at` set); audit event.

### R2 — Participants
**Statement:** Meetings track internal users (linked to `users.id`) and external invitees (email string).

**Scenarios:**
1. POST /meetings/{id}/participants with `{user_id, role}` → 201; duplicate → 409.
2. External: POST with `{email, role}` → 201. Email-only; no user auto-creation.
3. DELETE /meetings/{id}/participants/{participant_id} with `meeting.participant_manage` → 204.
4. Role in meeting: `organizer` | `presenter` | `attendee`.

### R3 — Status lifecycle
**Statement:** FSM `scheduled → in_progress → finished`, plus `cancelled` from any non-terminal state.

**Scenarios:**
1. PATCH /meetings/{id} with `status: X` → 422 `INVALID_STATUS_TRANSITION` if not allowed.
2. Same status → 200 idempotent (no-op, no audit event).
3. Timezone: stored as UTC; input/output ISO 8601 with offset (America/Bogota).

### R4 — Tenant isolation
**Statement:** No meeting or participant of tenant B is visible/mutable from tenant A's tokens.

**Scenarios:** cross-tenant GET/PATCH/POST/DELETE of any meeting or participant resource → 404 (`MEETING_NOT_FOUND` / `PARTICIPANT_NOT_FOUND`); never 403.

### R5 — Frontend
**Statement:** Portal shows meetings list + detail + create/edit forms using `/api/v1/meetings`.

**Scenarios:**
1. List page renders items with title, date (formatted America/Bogota), status badge.
2. Create form: validation client-side; server errors rendered from `code` + `message`.
3. Detail page: participants managements (add/remove internal+external), status badge, actions (cancel only when allowed).

## Out of scope

- recordings, transcription, AI, minutes, notifications, recurrence, convocatoria document.
