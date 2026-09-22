# Data model — meetings-recording-upload

## Migration 0006

```text
recordings (
  id                uuid PK default gen_random_uuid()
  meeting_id        uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE
  tenant_id         uuid NOT NULL REFERENCES organizations(id)
  filename          text NOT NULL
  content_type      text NOT NULL
  size_bytes        bigint NOT NULL CHECK (size_bytes > 0)
  sha256            char(64) NOT NULL
  storage_path      text NOT NULL UNIQUE
  duration_seconds  int NULL
  status            text NOT NULL DEFAULT 'stored'
                    CHECK (status IN ('stored','queued','transcribing','transcribed','failed'))
  uploaded_by       uuid NOT NULL REFERENCES users(id)
  created_at        timestamptz NOT NULL DEFAULT now()
  updated_at        timestamptz NOT NULL DEFAULT now()
  deleted_at        timestamptz NULL
)
CREATE UNIQUE INDEX ux_recordings_meeting_sha256
  ON recordings (meeting_id, sha256) WHERE deleted_at IS NULL;
CREATE INDEX ix_recordings_tenant ON recordings (tenant_id);
```

```text
jobs (
  id            uuid PK default gen_random_uuid()
  type          text NOT NULL               -- 'process_recording'
  payload       jsonb NOT NULL               -- { recording_id, meeting_id, tenant_id }
  status        text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','done','failed'))
  attempts      int NOT NULL DEFAULT 0
  max_attempts  int NOT NULL DEFAULT 5
  run_at        timestamptz NOT NULL DEFAULT now()
  locked_by     text NULL
  locked_at     timestamptz NULL
  completed_at  timestamptz NULL
  created_at    timestamptz NOT NULL DEFAULT now()
  updated_at    timestamptz NOT NULL DEFAULT now()
)
CREATE INDEX ix_jobs_pending ON jobs (run_at) WHERE status = 'pending';
```

## Multi-tenant rules

- `recordings.tenant_id` matches `meetings.organization_id` of the parent meeting.
- `jobs` rows carry `payload.tenant_id` for auditing; DB-level tenant filtering not needed (jobs are internal).
- Migrations must not carry tenant-specific rows; only schema + permissions.

## Timezone

UTC everywhere; UI formats in America/Bogota.
