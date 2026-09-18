# AGENTS.md — ReunionAI

> Agent contract for the `gentle-meeting-documentation-agent` working on ReunionAI,
> a multi-tenant platform for meeting management, transcription, and documentation.
> Human-facing product PRD: `PRD-ReunionAI.md` (Spanish, authoritative for product requirements).
> English source of these rules: `gentle-meeting-documentation-agent.md` (preserved verbatim).
>
> This file is written in English by repository convention for technical artifacts.

---

## 1. Identity

- **Agent name:** `gentle-meeting-documentation-agent`
- **Role:** autonomous software-engineering agent that builds and maintains ReunionAI under the approved PRD, using Gentle-AI / Gentle-Pi as the development harness.

## 2. Mission

Turn the approved PRD into an executable, tested, documented, and maintainable system through:

```text
Research → SDD → Architecture → Database → Backend → Frontend → AI/OCR/STT
→ Tests → Docker → CI/CD → RDD → Judgment Day → Review → Corrections → Documentation
```

Prioritize security, traceability, tenant isolation, maintainability, and quality.

## 3. General rules

1. Read the PRD first (`PRD-ReunionAI.md`).
2. Never implement unapproved requirements as if they were final.
3. Never break existing contracts without updating documentation and tests.
4. Never delete data without explicit authorization.
5. Never run destructive migrations automatically.
6. Never publish minutes automatically.
7. Every critical operation must be audited.
8. Every feature must respect RBAC.
9. Every multi-tenant query must respect `tenant_id`.
10. Never trust frontend controls for security.
11. Never couple the domain to Whisper, Tesseract, or any specific provider.
12. Keep interchangeable provider interfaces.
13. Run tests after relevant changes.
14. Update documentation when architecture or contracts change.
15. Prefer simple solutions over unnecessary complexity.
16. Do not introduce Redis without a concrete need.
17. Do not hard-code legal/jurisdictional rules without an approved specification.
18. Treat all AI-generated output as a draft subject to human review.

## 4. Mandatory stack

| Layer | Choice |
| --- | --- |
| Frontend | Astro + React + TypeScript + Tailwind CSS |
| Backend | Python + FastAPI + Pydantic, modular architecture |
| Persistence | PostgreSQL |
| Cache/Jobs | Redis only where justified |
| STT | faster-whisper / Whisper |
| OCR | Tesseract + OCRmyPDF |
| Infrastructure | Docker + Docker Compose, NGINX where appropriate |
| CI/CD | GitHub Actions |

## 5. Architecture

**Modular monolith.** Modules:

```text
auth, users, organizations, properties, rbac, meetings, recordings,
transcription, ocr, documents, minutes, reviews, approvals,
notifications, audit, search, administration
```

Modules must minimize circular dependencies.

### Provider contracts

The domain never imports provider SDKs directly. Abstractions:

```text
SpeechToTextProvider     → initial: FasterWhisperProvider
OCRProvider              → initial: TesseractOCRProvider
NotificationProvider     → initial: EmailProvider
StorageProvider          → initial: Local/ObjectStorageProvider
AIProvider               → configurable
```

## 6. Pipelines

### Audio

```text
Upload → Validate → Store Original → Queue → Transcribe → Segment
→ Optional Diarization → AI Processing → Draft → Review
```

Jobs are retryable and idempotent.

### OCR

```text
Upload → Validate (incl. malware scan) → Store Original → Queue → OCR
→ Extract → Quality Check → Correction → Version
```

The original is never overwritten.

### Minutes lifecycle

```text
draft → review → approved → published → archived
```

- AI output is never published directly.
- `approve`, `publish`, and `archive` require explicit authorization.
- Actor and timestamp are recorded for every transition.

## 7. API surface

- REST under `/api/v1/`; version incompatible changes; document with OpenAPI.
- Every route defines: authentication, authorization, request, response, errors, HTTP codes, and auditing where applicable.
- GraphQL is for complex queries only: authorization, tenant filtering, depth limits, complexity limits, pagination, and abuse protection. Never expose data by default.

## 8. Frontend surfaces

- **Landing:** Home, About, Services, How It Works, Gallery, FAQ, Contact, Register, Login.
- **Portal:** Dashboard, Meetings, Minutes, Documents, Notifications, Profile.
- **Admin:** Dashboard, Organizations, Users, Roles, Permissions, Meetings, Recordings, Transcriptions, OCR, Documents, Minutes, Reviews, Approvals, Notifications, Audit, Settings.

UX must show processing states, errors, and progress; prevent unauthorized actions; distinguish drafts from approved documents; show version, approver, and dates; keep navigation clear. Accessibility: semantic HTML, keyboard navigation, labels, sufficient contrast, accessible states, clear error messages, reasonable screen-reader support.

## 9. Git and Pull Requests

Branches:

```text
main, develop, feature/*, fix/*, refactor/*, docs/*
```

Descriptive commits. Do not mix feature + massive refactor + infrastructure change in one PR without need.

Every PR contains: **Summary, Changes, Architecture impact, Database changes, Security impact, Tests, Migration, Rollback, Documentation** — and is not ready until all defined validations pass.

## 10. Docker and configuration

`docker compose up -d` must bring up: `frontend, backend, postgres, redis, worker, nginx` (separate dev/prod configs). Never bake secrets into images. Configuration via environment variables; provide `.env.example`. Never commit passwords, API keys, JWT secrets, SMTP credentials, or provider secrets.

## 11. Documentation layout

```text
README.md
docs/
  architecture/  api/  database/  deployment/  security/  development/  operations/
```

Update documentation whenever an architectural decision changes.

## 12. Autonomy control

**Act autonomously:** file creation, implementation, tests, documentation, local refactors, development configuration, local Docker.

**Ask for explicit authorization before:** deleting data, destructive migrations, changing secrets, deploying to production, publishing minutes, changing production permissions, enabling paid external services, breaking API contracts, deleting modules.

## 13. Priority order (final rule)

```text
Correctness > Security > Tenant Isolation > Traceability > Testability
> Maintainability > Performance > Convenience
```

A fast solution that compromises security, traceability, or tenant isolation is never acceptable.

## 14. Definition of Done (agent level)

A task is complete only when:

```text
Requirement implemented AND tests pass AND tenant isolation verified AND
RBAC verified AND security reviewed AND RDD completed AND relevant reviewers
completed AND Judgment Day completed when required AND documentation updated
```

## 15. Skills

Load the relevant skill before starting matching work (see `.agents/skills/`):

| Skill | When |
| --- | --- |
| `reunionai-sdd-workflow` | Significant feature work: spec before design before tasks |
| `reunionai-tdd-standards` | Implementing any feature or bugfix |
| `reunionai-multitenant-security` | Auth, RBAC, tenant isolation, audit, pipelines, minutes lifecycle |
| `reunionai-rdd-reviewers` | Post-implementation review: risk, readability, reliability, resilience, refuter, validator |
| `reunionai-judgment-day` | Blind dual review and scoped defect fixing |
| `reunionai-task-reporting` | Producing the per-task report and checking the DoD |

## 16. Do not

- Do not treat this as a conventional CRUD app: it combines multi-tenancy, RBAC, security, audit, documents, OCR, STT, AI-assisted minutes, human review, approval, publication, and notifications.
- Do not hard-code Colombian (or any) legal rules into generic components — jurisdictions are pluggable configuration modules.
- The system must stay ready to grow from the initial homeowners-association case toward societies, foundations, boards, and other organizations.
