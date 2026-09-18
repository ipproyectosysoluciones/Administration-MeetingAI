# Agent Diagrams — Per-Module Development Flow

**Source:** `gentle-meeting-documentation-agent.md`, section 37 (verbatim Mermaid extraction).

Linear lifecycle for a single module/feature: requirement → SDD → domain →
database → API → frontend → integration → tests → RDD → reviewers →
Judgment Day → documentation.

```mermaid
flowchart LR
    A[Requirement] --> B[SDD]
    B --> C[Domain Model]
    C --> D[Database]
    D --> E[API]
    E --> F[Frontend]
    F --> G[Integration]
    G --> H[Tests]
    H --> I[RDD]
    I --> J[Reviewers]
    J --> K[Judgment Day]
    K --> L[Documentation]
    L --> M[Done]
```
