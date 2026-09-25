# Diagrams Index

Mermaid diagrams extracted verbatim from the authoritative source documents.
If a diagram changes, update the source document first and re-extract it here.

## Product (source: `PRD-ReunionAI.md`, Spanish)

| File | Source section | Content |
| --- | --- | --- |
| [product-frontend-flow.md](product-frontend-flow.md) | §42 | Landing → auth → RBAC → Portal/Admin; meeting → minutes → publication chain |
| [product-backend-flow.md](product-backend-flow.md) | §43 | Client → NGINX → REST/GraphQL → modules → DB/queues/workers/storage → review → publication |
| [product-full-flow.md](product-full-flow.md) | §44 | Full sequence: meeting, audio STT, OCR, AI draft, review, approval, notification, publication |

## Agent workflow (source: `gentle-meeting-documentation-agent.md`)

| File | Source section | Content |
| --- | --- | --- |
| [agent-flow.md](agent-flow.md) | §36 | PRD → SDD → TDD → tests → RDD → reviewers → Judgment Day → fix loop → PR |
| [agent-module-workflow.md](agent-module-workflow.md) | §37 | Per-module lifecycle from requirement to done |

## Current implementation (updated 2026-09-25)

| File | Source | Content |
| --- | --- | --- |
| [product-transcription-flow.md](product-transcription-flow.md) | PRs #66–86, meetings-transcription | Cadena MVP real: upload → queue → worker → draft → read API. **Actualizada por el RDD del 2026-09-24/25** (build-arg forwarding del worker, timeout por job, sin diarización). |

## Viewing

Mermaid renders natively on GitHub and in most Markdown viewers. For local
editing, any Mermaid-compatible editor (e.g. VS Code Mermaid extension,
mermaid.live) works.
