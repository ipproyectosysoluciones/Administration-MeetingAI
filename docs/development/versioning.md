# Versioning Policy — SemVer

This project follows [Semantic Versioning 2.0.0](https://semver.org/) (SemVer) for all public releases.

## Version format

`MAJOR.MINOR.PATCH`

## When to bump each part

| Component | Trigger |
| --- | --- |
| **MAJOR** | Incompatible API or schema changes. Breaking changes to public endpoints, data models, database migrations, or any backwards‑incompatible modification. |
| **MINOR** | New functionality added in a backwards‑compatible manner. New modules, features, integrations, or improvements that do not break existing contracts. |
| **PATCH** | Bug fixes, security patches, or backwards‑compatible internal changes. |

## Pre‑release tags

- Pre‑release tags (`-alpha`, `-beta`, `-rc`) **must never** be published on `main`.
- Pre‑releases are used for internal testing, CI validation, and early feedback only.
- A pre‑release version takes the form `MAJOR.MINOR.PATCH-alpha.1`, `MAJOR.MINOR.PATCH-beta.1`, etc.
- **While development is pre‑stable (0.x), versions use the form `v0.MINOR.PATCH-rc.N`** until the first stable `v1.0.0`. Example: `v0.1.0-rc.1`, `v0.2.3-rc.4`.

## Branching flow

- `feature/*` branches are created from `develop`, merged back into `develop` via pull requests.
- `hotfix/*` branches are created from `main` (or the latest released tag), fixed, and merged back into both `main` and `develop` (cherry‑pick).
- `main` only contains released, stable code. Releases are cut from `main` only.
- **`rc` (or `rc/x.y.z`) branches host release‑candidate tags `vMAJOR.MINOR.PATCH-rc.N`** and are used to stabilize code before a stable release.
- **`release` (or `release/x.y.z`) branches stabilize code before promoting to `main`**. Only code that has been verified on `release` may be merged into `main`.
- Pre‑release tags (`-rc.N`) may be cut from `rc`, `rc/*`, `release`, or `release/*` branches; stable tags only from `main`.

## Release process

1. **Only** from `main` may a stable release be cut.
2. Every release must have an immutable Git tag (e.g., `v1.2.3`).
3. Every release must have a corresponding GitHub Release with release notes.
4. Release notes are generated from **Conventional Commits** since the last tag.

## Conventional Commits

All commit messages **must** follow the Conventional Commits format:

```
<type>(optional scope): <description>

[optional body]

[optional footer(s)]
```

Recognized types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `style`, `ci`.

- A `feat` commit **always** triggers a MINOR bump (human‑approved in CI/CD).
- A `fix` commit **always** triggers a PATCH bump (human‑approved in CI/CD).
- A commit containing `BREAKING CHANGE` in its footer **always** triggers a MAJOR bump (human‑approved in CI/CD).
- `chore`, `style`, `refactor` without `BREAKING CHANGE` do not trigger a version bump automatically.

## Documentation versioning

Documentation is versioned together with the software and **must stay up to date**:

- Every **significant change** (new feature, altered contract, changed behavior, migration, security-relevant decision) **must** update the affected docs in the same PR. A feature PR is not complete with stale documentation.
- Documentation lives in the repository and therefore inherits the software version: each release tag (`vX.Y.Z` or `vX.Y.Z-rc.N`) also snapshots the documentation at that version.
- `docs/` carries the full history needed to derive **User Manuals** or **Developer Manuals** later; when those manuals are produced, they are generated from the docs of a specific release tag and carry that tag's version number.
- A `docs` commit without a functional change does not trigger a version bump; it rides along with the next release.

## CI/CD integration

The CI/CD pipeline (GitHub Actions) includes a `release` job that:

- Inspects the merge commit from `develop` → `main`.
- Proposes a version bump based on the types of commits since the last tag:
  - `feat` → proposes MINOR
  - `fix` → proposes PATCH
  - `BREAKING CHANGE` → proposes MAJOR
- Requires **human approval** before proceeding to tagging and publishing.
- Generates the GitHub Release notes from the commit body/footers.

## Summary table

| Commit type | Automatic bump | CI/CD job requirement |
| --- | --- | --- |
| `feat` | MINOR | Human‑approved |
| `fix` | PATCH | Human‑approved |
| `BREAKING CHANGE` | MAJOR | Human‑approved |
| `chore` | none | optional |
| `style` | none | optional |
| `refactor` | none | optional |
| `test` | none | optional |
| `docs` | none | optional |