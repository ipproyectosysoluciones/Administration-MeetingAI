# Product Diagrams — Meetings/Transcription (MVP, implemented)

Product of the merged slices (PRs #37–86). **Current implementation** shown, not the PRD future target.

```mermaid
flowchart TD
    U["Usuario / Cliente Astro+React"] --> NGINX["NGINX"]
    NGINX --> API["FastAPI /api/v1"]

    subgraph AuthZ["Auth/RBAC"]
        AUTH["DBAuthorizationResolver"]
    end

    API --> AUTH

    API -->|POST recordings upload| UP["RecordingService"]
    API -->|GET transcriptions| TR["TranscriptionService"]

    UP -->|store blob| ST["LocalStorageProvider"]
    UP -->|enqueue process_recording| Q["JobService"]

    Q -->|claim_next SKIP LOCKED| W["worker loop"]
    W -->|skip if draft| TR
    W -->|read blob| ST
    W -->|transcribe| FW["FasterWhisperProvider"]

    FW -->|draft transcript ok| TR
    FW -->|PermanentTranscriptionError| TR

    subgraph DB["PostgreSQL"]
        ORG["organizations"]
        MT["meetings"]
        REC["recordings"]
        JOB["jobs"]
        TRX["transcriptions"]
        AUD["audit_log"]
    end

    TR --> TRX
    Q --> JOB
    API --> AUD
    W --> AUD
```

**Notas de la versión actual** (lineage RDD review-52fc6f3f172a0f56, aprobado):

- El worker precalienta el whisper via build arg en `Dockerfile.worker` (no depende de red en el primer job).
- `TRANSCRIBE_TIMEOUT_SECONDS` limita la llamada al provider.
- No hay diarización en el MVP (sólo texto como dato; quién dijo qué queda fuera del primer change).

