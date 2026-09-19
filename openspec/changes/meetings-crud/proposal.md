# Proposal — meetings-crud

**Status:** proposed (user-approved scope; SDD optional per ODD, recorded because it crosses reviews).

## Problem statement

ReunionAI MVP auth-foundation is complete. Organizations cannot yet register meetings, invite participants, or manage their lifecycle; the product core remains unusable without this. PRD "ReunionAI" §meetings requires a tenant-scoped meetings register that feeds the future transcription and minutes pipeline.

## Why now

The meetings module is the entry point of every downstream artifact: recording uploads, transcription jobs, minutes drafts, and approvals all hang from a meeting entity. Without it, the backend serves no business value.

## Scope (in)

- **Meetings CRUD** — create, read (list/detail), update, cancel, tenant-scoped, RBAC-gated, audited.
- **Meeting entity:** title, description, date, start/end time, location, modality (in-person/virtual/hybrid), status, convocatoria-free (associated document later).
- **Participants:** internal users (role in meeting: organizer/presenter/attendee) + external invitees (email only, no account).
- **Permissions:** `meeting.read/create/update/cancel` (plus optional `meeting.admin` for org-admin override), wired into the existing base role matrices.
- **Audit:** every mutating transition captured as audit event (tenant-scoped).
- **Portal UI (Astro/React):** meeting list + detail + create/edit form (including participants), error states, date/time in America/Bogota.

## Scope (out)

- Recording uploads (follow-up change: `meetings-recording-upload` — storage provider, job queue, retry).
- Transcription/diarization/AI drafts/minutes/approvals.
- Convocatoria as a formal document (lands in a documents change).
- Notifications/email delivery.
- Meeting recurrence.

## Decisions (user-confirmed during explore)

| Decision | Value |
|---|---|
| Delivery split | 2 changes total: this one + follow-up `meetings-recording-upload` |
| Storage (later) | LocalStorageProvider behind interface; S3 unaffected in domain |
| Job queue (later) | Postgres-backed job table, idempotent, worker process |
| Audio formats (later) | mp3 / wav / m4a / ogg |
| Participants | internal users + external email invitees |
| Convocatoria | associated document, not a meetings field |
| Timezone | America/Bogota for display and scheduling rules |

## Risks

- IDOR: meeting IDs are tenant-scoped in every query (never trust the client).
- Status transitions only via service methods (no direct PATCH of `status`).
- External invitees: email stored, never auto-created as users; no password provisioning by implication.
- Review workload: unchanged per-slice budget ≤ 400 lines; chain PRs if exceeded.
- Timezone: store UTC in DB, convert at edges (input/output), never store wall-clock strings.

## Rollout notes

- 1 migration (meetings + meeting_participants) + seeds for new permissions.
- tests: unit services + integration CRUD + RBAC + cross-tenant isolation cases.
- Follow-up change `meetings-recording-upload` kept as separate change and separate issue.

## Success criteria

- A tenant admin can create/update/cancel meetings with participants; the list/detail UI is usable and errors are surfaced.
- Cross-tenant isolation tests prove no meeting of tenant B is visible/editable from tenant A (404, not 403).
- Every mutation produces exactly one audit event for the acting tenant.
