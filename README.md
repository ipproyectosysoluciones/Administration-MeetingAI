# ReunionAI — Administration-MeetingAI

<!-- badges:start --><p align="center">
  <a href="https://github.com/Gentleman-Programming/gentle-ai">
    <img width="220" src="https://raw.githubusercontent.com/Gentleman-Programming/gentle-ai/main/docs/assets/brand/built-with-gentle-ai.png" alt="Built with Gentle-AI" />
  </a>
</p>

<p align="center"><img alt="version" src="https://img.shields.io/badge/version-v0.1.0--rc-orange" />  <img alt="python" src="https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white" />  <img alt="fastapi" src="https://img.shields.io/badge/fastapi-0.110-009688?logo=fastapi&logoColor=white" />  <img alt="postgresql" src="https://img.shields.io/badge/postgresql-16-4169E1?logo=postgresql&logoColor=white" />  <img alt="astro" src="https://img.shields.io/badge/astro-7-BC52EE?logo=astro&logoColor=white" />  <img alt="react" src="https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=white" />  <img alt="typescript" src="https://img.shields.io/badge/typescript-5.6-3178C6?logo=typescript&logoColor=white" />  <img alt="tailwindcss" src="https://img.shields.io/badge/tailwindcss-3.4-06B6D4?logo=tailwindcss&logoColor=white" />  <img alt="docker_compose" src="https://img.shields.io/badge/docker_compose-ready-2496ED?logo=docker&logoColor=white" /></p>
<!-- badges:end -->

**[Español](#español) · [English](#english)**

---

## Español

Plataforma **multi-tenant** para gestionar reuniones formales, grabaciones, documentos, transcripciones, actas, aprobaciones, publicaciones y notificaciones. Orientada inicialmente a propiedad horizontal en Colombia, con arquitectura agnóstica de sector preparada para fundaciones, sociedades, juntas y otras organizaciones.

### Capacidades principales

- **Speech-to-Text:** grabaciones de reuniones → transcripciones (Whisper / faster-whisper).
- **OCR:** documentos escaneados o imágenes → texto estructurado (Tesseract + OCRmyPDF).
- **Actas asistidas por IA:** borradores con resumen, decisiones, acuerdos y tareas — siempre sujetos a revisión y aprobación humana antes de publicarse.
- **RBAC + MFA/2FA, auditoría completa y aislamiento de tenant:** ningún tenant puede acceder a datos de otro.
- **Portal privado, landing configurable y notificaciones por email** (WhatsApp/Telegram preparados para V2).

### Stack

| Capa | Tecnología |
| --- | --- |
| Frontend | Astro + React + TypeScript + Tailwind CSS |
| Backend | Python + FastAPI + Pydantic (monolito modular) |
| API | REST (`/api/v1/`) + GraphQL |
| Base de datos | PostgreSQL |
| Cache/colas | Redis (opcional, donde aporte valor) |
| Infraestructura | Docker + Docker Compose + NGINX |
| CI/CD | GitHub Actions |

Los proveedores (STT, OCR, notificaciones, storage, IA) se acceden mediante interfaces intercambiables: el dominio nunca depende de un SDK específico.

### Flujo completo del producto

```mermaid
sequenceDiagram
    actor Usuario
    participant Frontend
    participant API
    participant DB as PostgreSQL
    participant Queue as Redis/Queue
    participant Worker
    participant STT as Whisper
    participant OCR
    participant AI
    participant Storage
    participant Email

    Usuario->>Frontend: Crea reunión
    Frontend->>API: Crear reunión
    API->>DB: Persistir reunión

    Usuario->>Frontend: Carga audio
    Frontend->>API: Upload
    API->>Storage: Guardar original
    API->>Queue: Crear job STT

    Queue->>Worker: Procesar audio
    Worker->>STT: Transcribir
    STT-->>Worker: Segmentos
    Worker->>DB: Guardar transcripción
    Worker->>AI: Procesar contenido
    AI-->>Worker: Resumen/acuerdos/tareas
    Worker->>DB: Guardar resultados

    Usuario->>Frontend: Carga documento
    Frontend->>API: Upload documento
    API->>Storage: Guardar original
    API->>Queue: Crear job OCR

    Queue->>Worker: Procesar OCR
    Worker->>OCR: Extraer texto
    OCR-->>Worker: Texto OCR
    Worker->>DB: Guardar resultado

    Usuario->>Frontend: Solicita borrador
    Frontend->>API: Generar acta
    API->>AI: Crear borrador
    AI-->>API: Acta
    API->>DB: Guardar versión

    Usuario->>Frontend: Revisa
    Frontend->>API: Correcciones
    API->>DB: Nueva versión

    Usuario->>Frontend: Aprueba
    Frontend->>API: Aprobar
    API->>DB: Registrar aprobación

    API->>Email: Notificar
    API->>DB: Publicar acta
    Frontend-->>Usuario: Acta disponible
```

Más diagramas (flujo frontend, flujo backend, flujos del agente): **[docs/diagrams/](docs/diagrams/README.md)**.

### Documentación

| Documento | Descripción |
| --- | --- |
| [PRD-ReunionAI.md](PRD-ReunionAI.md) | Product Requirements Document (español, fuente autoritativa del producto) |
| [gentle-meeting-documentation-agent.md](gentle-meeting-documentation-agent.md) | Especificación completa del agente de desarrollo |
| [AGENTS.md](AGENTS.md) | Contrato del agente en inglés (reglas, stack, autonomía, Definition of Done) |
| [.agents/skills/](.agents/skills/) | Skills del agente: SDD, TDD, seguridad multi-tenant, RDD/reviewers, Judgment Day, reportes |
| [docs/diagrams/](docs/diagrams/README.md) | Diagramas Mermaid extraídos del PRD y del spec del agente |

### Desarrollo

El desarrollo sigue el ciclo **Research → SDD → TDD → RDD → Judgment Day → Review → Docs**, orquestado por el agente según `AGENTS.md`. Orden de prioridad innegociable:

```text
Correctness > Security > Tenant Isolation > Traceability > Testability
> Maintainability > Performance > Convenience
```

[Versioning policy](docs/development/versioning.md)

Entorno local:

```bash
cp .env.example .env          # configurar variables (JWT keys, DB, rate limits)
docker compose up -d          # frontend (:8081), backend, postgres, nginx
```

Desarrollo sin Docker:

```bash
# Backend (Python 3.11+)
cd apps/backend
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
# DB de tests (una vez):
docker run -d --name reunionai-test-pg -e POSTGRES_USER=reunionai \
  -e POSTGRES_PASSWORD=reunionai -e POSTGRES_DB=reunionai -p 5433:5432 postgres:16-alpine
.venv/bin/ruff check . && .venv/bin/mypy app && .venv/bin/pytest

# Frontend (pnpm)
cd apps/frontend
pnpm install && pnpm vitest run && pnpm dev
```

Bootstrap del primer super-admin de plataforma:

```bash
cd apps/backend
.venv/bin/python -m app.cli bootstrap-superadmin \
  --email admin@ejemplo.com --password <secreto> --full-name "Admin"
# o dentro de Docker: docker compose exec backend python -m app.cli bootstrap-superadmin ...
```

CI: `.github/workflows/ci.yml` corre lint + typecheck + tests + build en cada push/PR.

---

## English

**Multi-tenant** platform for managing formal meetings, recordings, documents, transcriptions, minutes, approvals, publications, and notifications. Initially targets homeowners associations in Colombia, with a sector-agnostic architecture ready for foundations, corporations, boards, and other organizations.

### Core capabilities

- **Speech-to-Text:** meeting recordings → transcripts (Whisper / faster-whisper).
- **OCR:** scanned documents and images → structured text (Tesseract + OCRmyPDF).
- **AI-assisted minutes:** drafts with summaries, decisions, agreements, and tasks — always subject to human review and approval before publication.
- **RBAC + MFA/2FA, full audit trail, and tenant isolation:** one tenant can never access another tenant's data.
- **Private portal, configurable landing page, and email notifications** (WhatsApp/Telegram adapters prepared for V2).

### Stack

| Layer | Technology |
| --- | --- |
| Frontend | Astro + React + TypeScript + Tailwind CSS |
| Backend | Python + FastAPI + Pydantic (modular monolith) |
| API | REST (`/api/v1/`) + GraphQL |
| Database | PostgreSQL |
| Cache/queues | Redis (optional, where it adds value) |
| Infrastructure | Docker + Docker Compose + NGINX |
| CI/CD | GitHub Actions |

All providers (STT, OCR, notifications, storage, AI) are accessed through interchangeable interfaces: the domain never depends on a specific SDK.

### Full product flow

See the sequence diagram above (Spanish section). All diagrams — including frontend flow, backend flow, and the agent workflows — live in **[docs/diagrams/](docs/diagrams/README.md)**.

### Documentation

| Document | Description |
| --- | --- |
| [PRD-ReunionAI.md](PRD-ReunionAI.md) | Product Requirements Document (Spanish, authoritative product source) |
| [gentle-meeting-documentation-agent.md](gentle-meeting-documentation-agent.md) | Full development-agent specification |
| [AGENTS.md](AGENTS.md) | Agent contract in English (rules, stack, autonomy, Definition of Done) |
| [.agents/skills/](.agents/skills/) | Agent skills: SDD, TDD, multi-tenant security, RDD/reviewers, Judgment Day, reporting |
| [docs/diagrams/](docs/diagrams/README.md) | Mermaid diagrams extracted from the PRD and the agent spec |

### Development

Work follows the **Research → SDD → TDD → RDD → Judgment Day → Review → Docs** cycle, orchestrated by the agent per `AGENTS.md`. Non-negotiable priority order:

```text
Correctness > Security > Tenant Isolation > Traceability > Testability
> Maintainability > Performance > Convenience
```

Local environment:

```bash
cp .env.example .env          # configure variables (JWT keys, DB, rate limits)
docker compose up -d          # frontend (:8081), backend, postgres, nginx
```

Development without Docker:

```bash
# Backend (Python 3.11+)
cd apps/backend
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
docker run -d --name reunionai-test-pg -e POSTGRES_USER=reunionai \
  -e POSTGRES_PASSWORD=reunionai -e POSTGRES_DB=reunionai -p 5433:5432 postgres:16-alpine
.venv/bin/ruff check . && .venv/bin/mypy app && .venv/bin/pytest

# Frontend (pnpm)
cd apps/frontend
pnpm install && pnpm vitest run && pnpm dev
```

Bootstrap the first platform super-admin:

```bash
cd apps/backend
.venv/bin/python -m app.cli bootstrap-superadmin \
  --email admin@example.com --password <secret> --full-name "Admin"
```

CI: `.github/workflows/ci.yml` runs lint + typecheck + tests + build on every push/PR.

---

> This software is not a substitute for legal advice. All AI-generated content is a draft subject to human review. / Este software no sustituye asesoría jurídica. Todo contenido generado por IA es un borrador sujeto a revisión humana.
