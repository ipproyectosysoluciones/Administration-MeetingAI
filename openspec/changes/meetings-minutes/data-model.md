# Data model — meetings-minutes

## `minutes` table (migration 0009)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, `gen_random_uuid()` | |
| `meeting_id` | UUID | FK `meetings.id` ON DELETE CASCADE, NOT NULL | |
| `tenant_id` | UUID | FK `organizations.id` ON DELETE CASCADE, NOT NULL | tenant root |
| `title` | VARCHAR(200) | NOT NULL | advisory R3-empty-title: no `min_length` yet |
| `content` | TEXT | NOT NULL, default `''` | |
| `version` | INT | NOT NULL, default 1, CHECK `version >= 1` | successive drafts per meeting |
| `status` | VARCHAR(16) | NOT NULL, default `'draft'`, CHECK in lifecycle | draft/review/approved/published/archived |
| `created_by` | UUID | FK `users.id`, NOT NULL | |
| `reviewed_by` | UUID | FK `users.id`, NULL | |
| `reviewed_at` | TIMESTAMPTZ | NULL | |
| `approved_by` | UUID | FK `users.id`, NULL | |
| `approved_at` | TIMESTAMPTZ | NULL | |
| `approved_ip` | TEXT | NULL | audit trail |
| `approved_user_agent` | TEXT | NULL | audit trail |
| `published_by` | UUID | FK `users.id`, NULL | |
| `published_at` | TIMESTAMPTZ | NULL | |
| `archived_at` | TIMESTAMPTZ | NULL | |
| `ai_provider` | TEXT | NULL | provenance |
| `ai_model` | TEXT | NULL | provenance |
| `ai_request_id` | TEXT | NULL | provenance |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now() | |

Indexes: `ix_minutes_tenant_id`, `ix_minutes_meeting_id`, `ix_minutes_status`.

## ORM alignment note

The `Minute` model uses `DateTime(timezone=True)` for every timestamp column to match `TIMESTAMPTZ`. An earlier draft used naive `mapped_column()` (no timezone) and a phantom `payload` JSONB column; both were corrected in MIN-103 (naive datetimes caused asyncpg `DataError` on insert; `payload` was not in the migration).

## Permission seeds

`minutes.read`, `minutes.write`, `minutes.approve`, `minutes.publish` (all `is_system=TRUE`, resource=`minutes`).

Role matrix:

| Role | read | write | approve | publish |
|---|---|---|---|---|
| super_admin | ✓ | ✓ | ✓ | ✓ |
| org_admin | ✓ | ✓ | ✓ | ✓ |
| secretary | ✓ | ✓ | — | — |
| president | ✓ | — | — | — |
| board_member | — | — | — | — |
| resident | — | — | — | — |
