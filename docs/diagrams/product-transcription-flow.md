# Product Diagrams — Meetings/Transcription (MVP, implemented)

Product of the merged slices (PRs #37–86). **Current implementation** shown,
not the PRD future target.

```mermaid
flowchart TD
    U[Usuario / Cliente Astro+React] --> NGINX[NGINX]
    NGINX --> API[FastAPI /api/v1]

    subgraph AuthZ[Auth/RBAC]
        API -->|JWT + transcription.read/create| AUTH[DBAuthorizationResolver]
    end

    API -->|POST /meetings/{id}/recordings| UP[RecordingService]
    API -->|GET /recordings/{id}/transcriptions<br/>GET /transcriptions/{id}| TR[TranscriptionService]
    UP -->|store blob| ST[LocalStorageProvider]
    UP -->|enqueue process_recording| Q[JobService]

    Q -->|claim_next (SKIP LOCKED)| W[worker loop]
    W -->|skip-if-draft| TR
    W -->|read blob| ST
    W -->|transcribe| FW[FasterWhisperProvider]

    FW -->|draft transcript| TR
    FW -->|PermanentTranscriptionError<br/>(actor/timestamps audit)| TR

    subgraph DB[(PostgreSQL)]
        ORG[organizations]
        MT[meetings]
        REC[recordings]
        JOB[jobs]
        TRX[transcriptions]
        AUD[audit_log]
    end

    TR --> TRX
    Q --> JOB
    API --> AUD
    W --> AUD
```

**Errata actualizados por el RDD de hoy** (lineage review-52fc6f3f172a0f56, aprobado
tras 3 rondas): el flujo en `docker-compose` usa `WHISPER_MODEL` igual al
pre-bake del `Dockerfile.worker` (ver compose: build arg forwarding), el timeout
`TRANSCRIBE_TIMEOUT_SECONDS` aplica por job, y **no hay diarización** en el MVP
(minutes usa el texto como, no quién dijo qué).
