# Architecture notes — meetings-crud

## Scope
Tenant-scoped meetings with participants (internal users + external invitees by email).

## Modules
- `apps/backend/app/modules/meetings/`: models (Meeting FSM: scheduled → in_progress → finished | cancelled), service (create/list/get/update/cancel with transitions validated), participants_service (internal + external channels exclusivas), routers with RBAC (`meeting.*` permissions).
- API: `/api/v1/meetings[...]` CRUD + `/cancel` + `/participants`; errors per api-contract.md (MEETING_NOT_FOUND 404 cross-tenant, INVALID_STATUS_TRANSITION 422, DUPLICATE_PARTICIPANT 409).

## Data model
- `meetings` table: organization_id FK, title, description, starts_at/ends_at UTC (validated ends>starts), location, modality (in_person|virtual|hybrid), status, soft-delete.
- `meeting_participants` table: meeting_id FK + either user_id FK or external_email (CHECK exactly-one-channel), role (organizer|presenter|attendee), unique per meeting+user/meeting+email.
- Migration 0005 + meeting.* permissions seeded; matrix: org_admin/secretary get full, president/board_member get read, resident nothing.

## Isolation
Integration matrix (TASK-240) extends isolation suite: GET/PATCH/cancel/participant-add/remove cross-tenant all 404; list scoped.

## Frontend
- Astro static pages: /meetings (list), /meetings/new (form), /meetings/detail?id=... (dynamic detail reads query param).
- React components: MeetingList (paginated search), MeetingCreateForm (validation), MeetingDetail (status badge, participants, cancel confirm).
- Access token persists in localStorage via session.ts after login.

## Tests
- Backend: 214 total (191 + 17 meetings/participants + extensions), incl. cross-tenant matrix.
- Frontend: 17 vitest (API client meetings + auth forms).

## Follow-ups
- Recordings upload (`meetings-recording-upload` change), transcription pipeline, minutes AI.
- Convocatoria documents as separate documents change.
