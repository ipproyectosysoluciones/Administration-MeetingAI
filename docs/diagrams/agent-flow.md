# Agent Diagrams — Agent Flow

**Source:** `gentle-meeting-documentation-agent.md`, section 36 (verbatim Mermaid extraction).

End-to-end agent loop: PRD → research → SDD → TDD → implementation → tests →
RDD → reviewers → Judgment Day → fix loop → documentation → PR → deploy.

```mermaid
flowchart TD
    A[PRD aprobado] --> B[Research]
    B --> C[SDD]
    C --> D[TDD]
    D --> E[Implementación]

    E --> F[Unit Tests]
    F --> G[Integration Tests]
    G --> H[Security Tests]
    H --> I[RDD]

    I --> J[review-risk]
    I --> K[review-reliability]
    I --> L[review-resilience]
    I --> M[review-readability]
    I --> N[review-refuter]
    I --> O[review-validator]

    J --> P[Judgment Day]
    K --> P
    L --> P
    M --> P
    N --> P
    O --> P

    P --> Q{¿Defectos?}

    Q -->|Sí| R[jd-fix-agent]
    R --> F

    Q -->|No| S[Documentation]
    S --> T[PR]
    T --> U[Merge / Deploy]
```
