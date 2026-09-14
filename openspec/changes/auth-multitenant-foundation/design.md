# Design — auth-multitenant-foundation

The design for this change is intentionally split into focused documents. All
files together constitute the design artifact; the SDD engine requires this
index file at the canonical `design.md` path.

- [architecture.md](architecture.md) — modular monolith layout, pipelines, provider contracts
- [data-model.md](data-model.md) — schema, tenancy keys, RBAC matrices
- [api-contract.md](api-contract.md) — REST surface under /api/v1, error and isolation conventions
- [test-plan.md](test-plan.md) — test layers, coverage matrix, TDD evidence expectations

Orchestrator resolution (recorded in apply-progress.md): these four files are
used as the design phase output in place of a monolithic design.md.
