# Security Policy

## Supported Versions

Only the latest release candidate is actively supported during the pre-stable phase. After the first stable release, the supported versions will be listed by minor line.

| Version | Supported |
|---------|-----------|
| latest `*-rc.*` | yes |
| everything older | no |

## Reporting a Vulnerability

Do not open a public issue. Report privately to the maintainers via the repository owner, or by opening a GitHub security advisory (Security → Report a vulnerability).

Include a description, the affected component/commit, and a reproduction path if you have one. Expect acknowledgement within 3 business days.

## Scope

This repository is multi-tenant. Credentials, API keys, JWT secrets, and tenant data must never be committed. `.env.example` is the only approved home for new config keys; secrets belong in env vars.
