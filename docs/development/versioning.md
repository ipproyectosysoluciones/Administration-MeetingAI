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

## Branching flow

- `feature/*` branches are created from `develop`, merged back into `develop` via pull requests.
- `hotfix/*` branches are created from `main` (or the latest released tag), fixed, and merged back into both `main` and `develop` (cherry‑pick).
- `main` only contains released, stable code. Releases are cut from `main` only.

## Release process

1. **Only** from `main` may a release be cut.
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