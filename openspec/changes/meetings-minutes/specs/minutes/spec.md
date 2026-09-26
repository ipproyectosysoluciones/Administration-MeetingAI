# Spec — meetings-minutes (delta specs)

Scope: OpenSpec delta for module `minutes`; conventions follow `meetings` / `transcription` / `recordings` (camelCase permission names, 404 cross-tenant, audit on every transition). Lifecycle: `draft → review → approved → published → archived`.

## Requirement R1 — Draft creation is tenant-scoped

A user with `minutes.write` MAY create a draft `Minute` for a meeting in their own tenant. `create_draft` MUST verify that `meeting_id` belongs to the caller's `tenant_id` (and is not soft-deleted) BEFORE inserting; otherwise it raises `404 MEETING_NOT_FOUND`. The new draft gets `version = (max existing version for that meeting) + 1`, `status="draft"`, and an audit event `minutes.draft.create`.

Scenarios:
1. **Happy path** — meeting in tenant → draft created with version 1, audit event recorded.
2. **Second draft** — an existing draft/approved minute for the meeting → new draft version increments.
3. **Cross-tenant meeting** — meeting in another tenant → 404, no row inserted, no audit.
4. **Nonexistent meeting UUID** — random UUID → 404 (not a foreign-key 500).

## Requirement R2 — Lifecycle transitions are guarded and audited

Each transition MUST reject an out-of-order state with `409 MINUTE_INVALID_STATE` and record an audit event with actor + ip + user_agent. The order is: `mark_reviewed` (draft→review), `approve` (review→approved, `minutes.approve`), `publish` (approved→published, `minutes.publish`), `archive` (published→archived, `minutes.publish`).

Scenarios:
1. **Full lifecycle** — draft→review→approved→published→archived succeeds; each hop sets its actor/timestamp fields.
2. **Invalid hop** — draft→approve (skipping review) → 409.
3. **Double transition** — publishing an already-published minute → 409.
4. **Actor recorded** — `approved_by`/`approved_at`/`approved_ip`/`approved_user_agent` populated on approve.

## Requirement R3 — Read/list endpoints are tenant-scoped

`get_for_tenant` and `list_for_meeting` MUST return only rows owned by the caller's tenant; a minute or meeting from another tenant yields `404` (never 403, to avoid leaking existence). Listing also validates the parent meeting exists in the tenant (404 `MEETING_NOT_FOUND`).

Scenarios:
1. **Own minute** → 200 with the full response.
2. **Foreign minute** → 404 `MINUTE_NOT_FOUND`.
3. **Foreign meeting in list** → 404 `MEETING_NOT_FOUND`.

## Requirement R4 — RBAC gates each surface

Routes enforce the dedicated permission: `minutes.read` (GET list/get), `minutes.write` (create draft, review), `minutes.approve` (approve), `minutes.publish` (publish, archive). Super-admin is a wildcard; tenant is always derived from `AuthContext.tenant_id`, never request-supplied.

Scenarios:
1. **org_admin/secretary** — has `minutes.write` → can create and review.
2. **resident without `minutes.approve`** → approve returns 403.
3. **No active membership** → 403 `NO_ACTIVE_MEMBERSHIP`.

## Requirement R5 — AI provider is a swappable contract

The domain depends only on the `AISummaryProvider` protocol (`summarize(transcript, meeting_title)`); `MockProvider` is the deterministic test/dev implementation. Real providers plug in without domain changes. AI output is always a draft subject to human review — never published directly.

Scenarios:
1. **Mock determinism** — same input → same summary.
2. **Empty transcript** — `MockProvider` raises `ValueError` (caller surfaces a controlled error).
