# Product Diagrams — Backend Flow

**Source:** `PRD-ReunionAI.md`, section 43 (verbatim Mermaid extraction).

Client → NGINX → REST/GraphQL → application modules → PostgreSQL, job queue,
workers (STT/OCR/AI/Email), and object storage; minutes end in the
review → approval → publication pipeline.

```mermaid
flowchart TD
    A[Cliente Astro/React] --> B[NGINX]
    B --> C[REST API]
    B --> D[GraphQL API]

    C --> E[Application Layer]
    D --> E

    E --> F[Auth/RBAC]
    E --> G[Organization]
    E --> H[Meeting]
    E --> I[Document]
    E --> J[Transcription]
    E --> K[OCR]
    E --> L[Minutes]
    E --> M[Notification]
    E --> N[Audit]

    F --> O[(PostgreSQL)]
    G --> O
    H --> O
    I --> O
    L --> O
    N --> O

    H --> P[Job Queue]
    I --> P
    J --> P
    K --> P
    M --> P

    P --> Q[(Redis)]
    P --> R[Worker]

    R --> S[Whisper/faster-whisper]
    R --> T[Tesseract/OCRmyPDF]
    R --> U[IA Processing]
    R --> V[Email Provider]

    S --> J
    T --> K
    U --> L
    V --> M

    I --> W[(Object Storage)]
    J --> W
    K --> W
    L --> W

    L --> X[Review]
    X --> Y[Approval]
    Y --> Z[Publication]
    Z --> A
```
