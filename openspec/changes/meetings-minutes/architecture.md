# Architecture — meetings-minutes

## Module layout

```
app/modules/minutes/
  __init__.py
  models.py        # Minute ORM model (migration 0009)
  providers.py     # AISummaryProvider protocol + MockProvider
  schemas.py       # Pydantic request/response models
  service.py       # MinutesService (lifecycle + tenant scoping)
  router.py        # REST surface (permission-gated)
```

Frontend:

```
apps/frontend/src/
  lib/minutes.ts                          # API client + types
  components/minutes/MinutesPanel.tsx      # list + transitions
  components/minutes/MinutesPanelLoader.tsx# reads meeting_id from URL
  pages/minutes/index.astro                # portal page
```

## Dependency direction

```
router → service → models
            ↓
        AuditService.record (audit module)
            ↓
        Meeting (meetings module, for ownership validation)
```

The domain never imports provider SDKs: `service.py` depends only on the `AISummaryProvider` protocol, not on `MockProvider` or any future real provider.

## Lifecycle state machine

```
draft → review → approved → published → archived
```

- Guarded by a CHECK constraint on `status`.
- Each transition is a service method that validates the current state (`409 MINUTE_INVALID_STATE` on out-of-order hops) and records an audit event with actor/ip/user_agent.
- `version` tracks successive drafts per meeting (`max+1`), not per-transition rows.

## Tenant isolation

- `AuthContext.tenant_id` is the sole tenant source (never request-supplied) — IDOR prevention.
- `create_draft` validates the meeting belongs to the tenant (`Meeting.id + organization_id + not deleted`) before insert.
- `get_for_tenant` / `list_for_meeting` scope by `tenant_id`; a foreign row yields `404` (never 403).

## RBAC

| Permission | Grants |
|---|---|
| `minutes.read` | GET list, GET single |
| `minutes.write` | POST create draft, POST review |
| `minutes.approve` | POST approve |
| `minutes.publish` | POST publish, POST archive |

Super-admin is a wildcard; the permission set is resolved per-request via `require_permission` (never trusted from the JWT hint).

## AI provider contract

```python
class AISummaryProvider(Protocol):
    async def summarize(self, *, transcript: str, meeting_title: str) -> str: ...
```

`MockProvider` is the deterministic dev/test implementation. Real providers (Claude/OpenAI/etc.) implement the same protocol without domain changes. AI output is always a draft for human review.
