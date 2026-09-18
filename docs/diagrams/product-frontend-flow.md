# Product Diagrams — Frontend Flow

**Source:** `PRD-ReunionAI.md`, section 42 (verbatim Mermaid extraction).

Landing → authentication → RBAC → Portal / Admin dashboards, including the
meeting → recording → transcription → minutes → publication chain.

```mermaid
flowchart TD
    A[Landing pública] --> B{Usuario}
    B -->|Visitante| C[Información pública]
    B -->|Registro| D[Registro]
    B -->|Login| E[Autenticación]

    D --> E
    E --> F{Autorización RBAC}

    F -->|Portal| G[Portal privado]
    F -->|Administración| H[Dashboard administrativo]

    G --> I[Reuniones]
    G --> J[Actas publicadas]
    G --> K[Documentos autorizados]
    G --> L[Notificaciones]
    G --> M[Perfil]

    H --> N[Organizaciones]
    H --> O[Usuarios y roles]
    H --> P[Reuniones]
    H --> Q[Grabaciones]
    H --> R[Transcripciones]
    H --> S[OCR y documentos]
    H --> T[Actas y revisiones]
    H --> U[Aprobaciones]
    H --> V[Auditoría]
    H --> W[Configuración]

    P --> Q
    Q --> R
    R --> T
    S --> T
    T --> X[Publicación]
    X --> J
    X --> L
```
