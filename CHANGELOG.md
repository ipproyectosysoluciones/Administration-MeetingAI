
## [0.1.0-rc.1] - 2026-09-25

### Features

- feat(ci): release.yml seeds first rc as 0.1.0-rc.1 and dispatches publish-images; publish-images gains workflow_dispatch + checkout on tagged ref
- feat(ci): publish container images to GHCR on v* tags (#83)
- feat(ci): publish-images workflow + OCI labels in Dockerfiles
- feat(worker): transcription worker service en docker-compose + docs (TASK-305) (#81)
- feat(worker): transcription worker service in docker-compose + docs (TASK-305)
- feat(transcription): read-only REST surface (TASK-304) (#72)
- feat(transcription): read-only REST surface (TASK-304)
- feat(recordings): enqueue process_recording on fresh upload (TASK-303) (#71)
- feat(recordings): enqueue process_recording on fresh upload (TASK-303)
- feat(transcription): Transcript model + service + worker loop (TASK-302) (#70)
- feat(transcription): Transcript model + service + worker loop (TASK-302)
- feat(transcription): SpeechToTextProvider port + FasterWhisperProvider (TASK-301) (#68)
- feat(transcription): SpeechToTextProvider port + FasterWhisperProvider (TASK-301)
- feat(transcription): migration 0007 transcriptions + transcription.* permissions (TASK-300) (#66)
- feat(transcription): migration 0007 transcriptions + transcription.* permissions (TASK-300)
- feat(recordings): meetings-recording-upload — storage, queue, portal (TASK-250..255) (#63)
- feat(frontend): recordings UI in meeting detail (TASK-254, S4) (#62)
- feat(frontend): recordings upload/download/list in meeting detail (TASK-254)
- feat(jobs): job queue service + tests (TASK-253)
- feat(recordings): S3 service + router (TASK-252) (#59)
- feat(recordings): storage provider port + local impl (TASK-251, S2) (#58)
- feat(recordings): S3 service + JWT wiring + full integration coverage (TASK-252)
- feat(recordings): storage provider, service, router, integration tests (TASK-251, TASK-252)
- feat(recordings): S2 service + REST router (upload/list/get/download/delete) + tests (TASK-252)
- feat(recordings): storage provider contract + local impl (TASK-251)
- feat(recordings): migration 0006 + recording.* permissions (TASK-250, S1) (#57)
- feat(recordings): migration 0006 (recordings+jobs) + recording.* permissions (TASK-250)
- feat(meetings): meetings-crud complete (TASK-200..242) — CRUD, participants, FSM, portal (#55)
- feat(frontend): meetings portal UI (TASK-230/231/232, S4) (#53)
- feat(frontend): meetings portal — list, create, detail + participants UI (TASK-230/231/232)
- feat(meetings): participants service + REST (TASK-220/221, S3) (#51)
- feat(meetings): participants service + REST + tests (TASK-220, TASK-221)
- feat(meetings): meetings module CRUD + FSM (S2, TASK-210/211) (#50)
- feat(meetings): service + REST CRUD + FSM + tenant scoping (TASK-210, TASK-211)
- feat(meetings): migration 0005 + meeting.* permissions (S1, TASK-200/201) (#49)
- feat(meetings): migration 0005 meetings/participants + meeting.* perms (TASK-200, TASK-201)
- feat: frontend auth screens + infra + CI (TASK-100..113) (#45)
- feat: super-admin bootstrap CLI with audit event (TASK-111)
- feat(frontend): login/register/MFA screens wired to /api/v1/auth (TASK-100)
- feat: super-admin bootstrap CLI with audit event (TASK-111)
- feat(frontend): login/register/MFA screens wired to /api/v1/auth (TASK-100)
- feat: audit service + admin query endpoint
- feat(rbac): role↔permission and user↔role assignments (TASK-070, slice ii)
- feat(rbac): permission registry + custom role CRUD (TASK-070, slice i)
- feat(organizations): property + membership CRUD (TASK-060 part 2)
- feat(organizations): org CRUD + super-admin soft-delete cascade (TASK-060 part 1)
- feat(users): tenant-scoped admin CRUD (TASK-050 part 2)
- feat(users): self-service profile + password change (TASK-050 part 1)
- feat(auth): session list/revoke + mandatory MFA for admin roles
- feat(auth): MFA TOTP setup/verify/disable/challenge + single-use recovery codes
- feat(auth): revoke/logout invalidates the current refresh token
- feat(auth): refresh rotates tokens and revokes chain on reuse
- feat(auth): login issues RS256 access + rotating refresh, MFA gate hook
- feat(auth): register creates org, org-admin, and seeds base role
- feat: ORM models and DB authorization resolver (PR-3 prerequisite)
- feat(core): require_permission dependency (401 vs 403)
- feat(core): tenant-context resolution chain
- feat(core): in-memory sliding-window rate limiter
- feat(core): JWT service RS256 (15-min access tokens)
- feat(core): password hashing service (Argon2id)
- feat: add core migrations 001-004 (init_core/auth/rbac/audit)

### Fixes

- fix(ci): release chain fixes (rc seed 0.1.0, dispatch publish-images) (#85)
- fix(ci): template-injection guards + checkout persist-credentials=false in release and publish workflows
- fix(ci): anchored strict-SemVer tag guard (RDD correction round 2)
- fix(ci): strict semver tag guard for image publish + yamllint pragmas (RDD round 2)
- fix(deps): SQLAlchemy 2.1 typing compatibility; unpin sqlalchemy (#82)
- fix(deps): SQLAlchemy 2.1 compatible Row typing; unpin sqlalchemy (issue #79)
- fix(deps): stt extra must live inside [project.optional-dependencies]
- fix(worker): bind baked whisper model to runtime env var (R3-ModelVersionMismatch)
- fix(worker): pre-download whisper model at image build (R3-ModelDownloadNoCacheStrategy)
- fix(worker): healthcheck, restart policy y límites de recursos (R3-1, escalated review)
- fix(deps): pin sqlalchemy<2.1 (restore CI mypy) — hotfix (#73)
- fix(deps): pin sqlalchemy<2.1 to restore CI mypy
- fix(transcription): RDD correction round 3 (service commit ownership + error taxonomy)
- fix(transcription): RDD correction round 2 (R3-1..R3-5)
- fix(scripts): robust version parsing in gen_readme_badges (RDD R3-1/R3-2)
- fix(scripts): clean error handling in gen_readme_badges (RDD R4-002)
- fix(release): RDD correction round 1 (6 findings)
- fix(frontend): astro7 static-safe detail page (query param)
- fix(security): Astro 7 + Vitest 4 + CI hardening (dependabot + CodeQL) (#47)
- fix(security): upgrade astro 7.3.3 + vitest 4.1.11 (close 20 dependabot alerts) (#46)
- fix(security): force cookie@^2 (astro 7 ESM compat) + build green
- fix(security): upgrade astro 4→7.3.3, vitest 2→4.1.11, react 19 (dependabot batch)
- fix: review findings — MFA enrollment path, slug 409, refresh race lock, rbac seed idempotency, track frontend lib
- fix: review findings — MFA enrollment path, slug 409, refresh race lock, rbac seed idempotency, track frontend lib
- fix(audit): enforce audit.read permission, mount router, fix pagination, add real integration tests

### Other

- chore(ci): yamllint pragmas for long SHA-pinned action lines
- docs(readme): centered Gentle-AI badge + stack badges + self-updating generator (#69)
- docs(readme): centered Gentle-AI badge + stack/version badges + generator
- docs: add Built with Gentle-AI badge to README (#67)
- docs: add Built with Gentle-AI badge to README
- ci(release): SemVer versioning policy + Release workflow (rc tags, docs versioning) (#65)
- test(rbac): revert premature seed-count bump (belongs to meetings-transcription)
- ci(release): add Release workflow with SemVer rc tagging
- chore: ignore odd/ local ODD task tracking
- docs: tick TASK-252/253 + rbac seed count sync
- docs: meetings-transcription proposal/spec/design/tasks (planning complete)
- docs: add versioning policy (SemVer) + initial CHANGELOG
- docs: close meetings-recording-upload (TASK-255)
- docs: tick TASK-254 (recordings portal merged)
- chore: ignore apps/backend/data runtime recordings
- chore: untrack test-generated recordings under apps/backend/data
- chore: close loop on recordings S3+S4 (jobs service/README) (#61)
- chore: python-multipart + task ticks
- chore: untrack apps/backend/data (runtime artifacts)
- chore: ignore test-generated recording data dir
- style: ruff format pass (recordings S1)
- docs: meetings-recording-upload SDD artifacts (proposal, spec, design, tasks)
- docs: close meetings-crud (TASK-240/241/242)
- docs: tick TASK-241
- docs: architecture notes for meetings-crud (TASK-241)
- docs: tick TASK-240 (isolation extension merged)
- test(isolation): meetings+participants cross-tenant (TASK-240) (#54)
- test(isolation): meetings+participants cross-tenant matrix (TASK-240)
- test(meetings): list pagination/search/auth (TASK-211 extra) (#52)
- test(meetings): pagination, search, auth gating (TASK-211 extra)
- docs: record S3 (TASK-220/221) apply progress
- docs: record S2 (TASK-210/211) apply progress
- style: cross-format pass for meetings S2
- docs: record S1 (TASK-200/201) apply progress
- style: format test_registry + meetings migration
- style: fix E501 in seed idempotency comment
- docs: meetings-crud SDD artifacts (proposal, spec, architecture, data-model, api-contract, test-plan, tasks)
- ci: node 22 for astro 7
- MVP: auth-multitenant-foundation (auth, RBAC, audit, aislamiento, frontend, infra) (#32)
- ci: add permissions block (CodeQL medium alerts)
- Merge branch 'feature/auth-multitenant-foundation-pr5-audit' of github.com:ipproyectosysoluciones/Administration-MeetingAI into develop
- ci: restore pnpm version pin on pr6 (lost in rebase)
- Merge branch 'feature/auth-multitenant-foundation-pr6-frontend' of github.com:ipproyectosysoluciones/Administration-MeetingAI into feature/auth-multitenant-foundation-pr6-frontend
- docs: add AGENTS.md agent contract and PRD
- test(bootstrap): delta-based assertions for full-suite DB sharing
- docs: README quickstart + architecture notes (TASK-113)
- chore: pin CI actions to commit SHAs (supply-chain)
- chore: GitHub Actions CI (lint, typecheck, unit+integration, build) (TASK-112)
- chore: docker-compose dev/prod stack with health smoke (TASK-110)
- style: prettier formatting on auth forms
- chore: ignore agent harness state (.pi, .agents, .windsurf, openspec/config.yaml)
- ci: backend packaging fix for CI install (cherry-picked pyproject)
- ci: add CI workflow to this slice (from develop)
- ci: pin pnpm/action-setup version (frontend job fix)
- docs: add AGENTS.md agent contract and PRD
- test(bootstrap): delta-based assertions for full-suite DB sharing
- docs: README quickstart + architecture notes (TASK-113)
- chore: pin CI actions to commit SHAs (supply-chain)
- chore: GitHub Actions CI (lint, typecheck, unit+integration, build) (TASK-112)
- chore: docker-compose dev/prod stack with health smoke (TASK-110)
- style: prettier formatting on auth forms
- chore: ignore agent harness state (.pi, .agents, .windsurf, openspec/config.yaml)
- test(isolation): cross-tenant isolation matrix (TASK-090)
- docs: add design.md index for split design artifacts (auth-multitenant-foundation)
- docs: record PR-4c (rbac module) apply progress (TASK-070)
- docs: record PR-4b (organizations module) apply progress (TASK-060)
- docs: record PR-3a (auth register/login/refresh/revoke) apply progress
- style: ruff-format auth integration tests
- docs: record PR-2 (Phases 2-3) apply progress
- docs: record Phase 1 (migrations) apply progress
- test: migration smoke, schema introspection, and append-only tests
- chore: add async SQLAlchemy + Alembic database foundation
- chore: switch frontend to pnpm, stop committing lockfiles
- chore: scaffold backend + frontend (auth-multitenant-foundation Phase 0)
- Initial commit

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- auth-multitenant-foundation MVP
- meetings-crud
- meetings-recording-upload
- security hardening: Astro 7/Vitest 4
- CI/CodeQL fixes

---

Pre-0.1.0 — project bootstrap, no tags exist yet.