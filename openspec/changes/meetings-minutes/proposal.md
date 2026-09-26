# Proposal — meetings-minutes

## Problem statement

Transcriptions and meetings exist, but the platform has no acta (minutes) artifact: no draft generation, no human review/approval, no publication, and no audit trail for the lifecycle the PRD §15 mandates (`Transcripción → Borrador → Revisión humana → Correcciones → Aprobación → Publicación`). This change introduces the minutes module — the entity, its lifecycle state machine, its permissions, its read/write REST surface, and the portal UI — while keeping AI drafting behind a provider contract.

## Why now

Minutes are the product's core deliverable: they turn stored transcriptions into reviewable, approvable, publishable documents. Everything downstream (approvals, notifications, document search) depends on a minutes artifact existing. Deferring it keeps the pipeline unfinished.

## Scope (in)

- **Migration 0009**: `minutes` table (tenant/meeting FKs, `title`, `content`, `version`, `status` lifecycle, audit actor/timestamp fields, AI provenance fields, timestamps) + `minutes.*` permission seeds (`minutes.read`, `minutes.write`, `minutes.approve`, `minutes.publish`) with role matrix.
- **`AISummaryProvider` protocol + `MockProvider`**: the domain never imports provider SDKs; real providers (claude/openai/…) plug in later without touching the domain.
- **`Minute` ORM model** (aligned with migration 0009: `DateTime(timezone=True)` for TIMESTAMPTZ).
- **`MinutesService`**: `create_draft` (meeting ownership validation + version increment), `mark_reviewed`, `approve`, `publish`, `archive`, `get_for_tenant` (404 cross-tenant), `list_for_meeting` (meeting validation + pagination).
- **REST**: `GET/POST /meetings/{meeting_id}/minutes`, `GET /minutes/{id}`, `POST /minutes/{id}/{review,approve,publish,archive}` — each gated by the corresponding `minutes.*` permission.
- **Frontend portal**: `lib/minutes.ts` client, `MinutesPanel` (list + lifecycle transitions + draft/approved distinction), `/minutes` page.
- **Audit**: `minutes.draft.create`, `minutes.review`, `minutes.approve`, `minutes.publish`, `minutes.archive` via `AuditService.record` (actor/ip/user_agent).

## Scope (out)

- AI draft generation wiring (transcription → `summarize()` → auto-draft): the port exists but nothing invokes it yet. Follow-up (MIN-105).
- Corrections/edit versioning beyond `version` increment (a correction is a new draft version, not in-place edit of an approved minute).
- Notifications on approval/publication.
- Document (OCR) inputs into a minute.

## Decisions locked

1. Lifecycle is **in-place status mutation** on one row (`draft → review → approved → published → archived`) guarded by a CHECK constraint; `version` tracks successive drafts per meeting, not per-transition rows. (Note: an early docstring claimed "append-only"; the audit *events* are append-only, the row is not — see advisory R3-append-only-not-implemented.)
2. Tenant scoping uses `tenant_id` (FK to `organizations.id`) matching the migration; meetings use `organization_id` for the same target — the service maps between them when validating ownership.
3. `approve`, `publish`, `archive` require their dedicated permission; `review` uses `minutes.write`.
4. AI-generated minutes are always drafts subject to human review — never published directly (AGENTS.md rule 6).

## Risks

- **Cross-tenant IDOR**: `create_draft` must verify meeting ownership before insert (fixed in review R3-cross-tenant-meeting-create).
- **Version race**: `version = max+1` has a race under concurrency; admitted, flagged as advisory R3-version-race (follow-up: per-meeting counter or unique constraint).
- **Empty title** accepted by the schema; flagged as advisory R3-empty-title (follow-up: `min_length=1`).
- Tenant scoping correctness relies on `AuthContext.tenant_id` (never a request-supplied tenant) — unchanged from the multitenant security contract.

## Success criteria

- A member with `minutes.write` can create a draft for a meeting in their tenant; a foreign meeting or random UUID yields a controlled 404, not a 500.
- The full lifecycle transitions with audit per event; each transition rejects an invalid state with 409 `MINUTE_INVALID_STATE`.
- Read/list endpoints are tenant-scoped (404 cross-tenant).
- Frontend distinguishes drafts from approved/published minutes and exposes the transitions.
