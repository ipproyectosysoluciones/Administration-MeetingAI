# ROADMAP

## Done

| Phase | Content | Ranges |
|-------|---------|--------|
| Auth multi-tenant foundation | auth, users, organizations, rbac, audit, login UI | PRs #37–45, issue n/a |
| Meetings CRUD | meetings + participants + FSM + portal | PRs #49–55, issue archived |
| Recordings upload | upload/download/list, jobs queue | PRs #57–63, issue #56 closed |
| Meetings transcription | PR #66→#81 migration+worker+read API | issues #64, #74–78 closed |
| Release chain | SemVer rc + GHCR publish on tags | PRs #65, #69, #83–85 |

## Next

- Minutes AI processing (the next PRD change): draft generation, human review, approval workflow, publication.

## Later

- OCR pipeline (documents → structured text)
- Search across meetings/recordings/transcripts
- Notifications module, administration module

## Incidents resolved

- SQLAlchemy 2.1 upstream breaking the mypy in organizations/users services — mitigated by `sqlalchemy>=2.0` unpin with `Row` aliasing fix (PR #82, issue #79 closed, SA 2.1 suite 260 green).
