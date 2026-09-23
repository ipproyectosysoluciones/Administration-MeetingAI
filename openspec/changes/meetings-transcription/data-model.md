# Data model — meetings-transcription

## Migration 0007 — transcripts table

```text
transcripts (
  id                uuid PK default gen_random_uuid()
  recording_id      uuid NOT NULL REFERENCES recordings(id) ON DELETE CASCADE
  meeting_id        uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE
  tenant_id         uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE
  language          text NOT NULL DEFAULT 'es'
  text              text NULL
  segments          jsonb NOT NULL DEFAULT '[]'
                   CHECK (jsonb_typeof(segments) = 'array')
                   CHECK (
                     SELECT count(*) = 0 FROM jsonb_array_elements(segments) e
                     WHERE (e->>'start') IS NULL
                        OR (e->>'end') IS NULL
                        OR (e->>'text') IS NULL
                   )
  avg_confidence    float NULL
  model_used        text NOT NULL DEFAULT 'small'
  version           integer NOT NULL DEFAULT 1
  status            text NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'final'))
  error             text NULL
  created_by_job_id uuid REFERENCES jobs(id) ON DELETE SET NULL
  created_at        timestamptz NOT NULL DEFAULT now()
  updated_at        timestamptz NOT NULL DEFAULT now()
  deleted_at        timestamptz NULL
)
CREATE INDEX ix_transcripts_tenant ON transcripts (tenant_id);
CREATE UNIQUE INDEX ux_transcripts_recording_draft
  ON transcripts (recording_id)
  WHERE status = 'draft';
```

## Permission seeds — `transcription.*`

```text
_transcription_permissions:
  ("transcription.read", "transcription", "read", "Read transcription metadata")
  ("transcription.create", "transcription", "create", "Create transcription (worker enqueue)")

_transcription_role_matrix:
  "super_admin":   frozenset({p[0] for p in _transcription_permissions}),
  "org_admin":     frozenset({p[0] for p in _transcription_permissions}),
  "secretary":     frozenset({"transcription.read", "transcription.create"}),
  "president":     frozenset({"transcription.read"}),
  "board_member":  frozenset(set()),   # none — explicitly resolved below
```

## Multi-tenant rules

- `transcripts.tenant_id` copies `recordings.tenant_id` (no cross-tenant reads possible).
- Recordings carry `tenant_id` from the parent meeting; transcripts inherit it.
- The unique index `ux_transcripts_recording_draft` enforces idempotency at DB level: only one draft transcript per recording.

> **Decision note**: The `board_member` role was pending decision in this change. Per the spec resolution below, board_member receives **no** transcription permissions (empty set), consistent with the principle that board members should not have STT access in v1. This is not a residual from an earlier board-member-permissions change — it is an explicit resolution.

## Resolution of board_member permission pending decision

The spec notes that `board_member` role permissions were pending. The resolution is:

- **board_member: none** (empty permission set) — explicitly no transcription read/create access.
- This is a deliberate v1 scoping decision: board members operate at the meeting level (meeting.read, meeting.write) but are excluded from AI/STT pipelines in this release.
- The notice: *“board_member receives no transcription permissions — explicit v1 scoping, not a residual.”*

## Seed script (alembic migration 0007)

```python
_transcription_permissions = [
    ("transcription.read", "transcription", "read", "Read transcription metadata"),
    ("transcription.create", "transcription", "create", "Create transcription (worker enqueue)"),
]

_transcription_role_matrix = {
    "super_admin":   frozenset(p[0] for p in _transcription_permissions),
    "org_admin":     frozenset(p[0] for p in _transcription_permissions),
    "secretary":     frozenset({"transcription.read", "transcription.create"}),
    "president":     frozenset({"transcription.read"}),
    "board_member":  frozenset(set()),  # explicitly none
}

def _seed_transcription_permissions() -> None:
    values = ",\n  ".join(
        f"(gen_random_uuid(), '{n}', '{r}', '{a}', '{d}', TRUE)"
        for n, r, a, d in _transcription_permissions
    )
    op.execute(
        "INSERT INTO permissions (id, name, resource, action, description, is_system)\n"
        f"VALUES {values}\n"
        "ON CONFLICT (name) DO NOTHING"
    )

def _seed_transcription_role_permissions() -> None:
    for role_name, perms in _transcription_role_matrix.items():
        if not perms:
            continue
        perm_list = ", ".join(f"'{p}'" for p in perms)
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id)\n"
            "SELECT r.id, p.id FROM roles r\n"
            "JOIN permissions p ON p.name IN (" + perm_list + ")\n"
            f"WHERE r.name = '{role_name}' AND r.organization_id IS NULL\n"
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )
```