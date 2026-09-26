# API contract — meetings-minutes

Base path: `/api/v1`. All routes require a Bearer token; the tenant is derived from the authenticated membership, never from a request body/param. Cross-tenant access yields `404` (existence never leaks).

## Endpoints

| Method | Path | Permission | Status | Notes |
|---|---|---|---|---|
| GET | `/meetings/{meeting_id}/minutes` | `minutes.read` | 200 | paginated list (validates meeting ownership → 404) |
| GET | `/minutes/{minute_id}` | `minutes.read` | 200 | 404 `MINUTE_NOT_FOUND` cross-tenant |
| POST | `/meetings/{meeting_id}/minutes` | `minutes.write` | 201 | create draft (validates meeting → 404) |
| POST | `/minutes/{minute_id}/review` | `minutes.write` | 200 | draft→review; 409 on invalid state |
| POST | `/minutes/{minute_id}/approve` | `minutes.approve` | 200 | review→approved; 409 on invalid state |
| POST | `/minutes/{minute_id}/publish` | `minutes.publish` | 200 | approved→published; 409 on invalid state |
| POST | `/minutes/{minute_id}/archive` | `minutes.publish` | 200 | published→archived; 409 on invalid state |

## Request bodies

`MinuteCreateRequest`:
```json
{
  "title": "Acta junta ordinaria",
  "content": "Se acordó votar el presupuesto.",
  "ai_provider": null,
  "ai_model": null,
  "ai_request_id": null
}
```

Transition endpoints take no body; `ip` and `user_agent` are read from the request (`request.client.host`, `User-Agent` header).

## Response — `MinuteResponse`

```json
{
  "id": "uuid",
  "meeting_id": "uuid",
  "tenant_id": "uuid",
  "title": "…",
  "content": "…",
  "version": 1,
  "status": "draft",
  "created_by": "uuid",
  "reviewed_by": null,
  "reviewed_at": null,
  "approved_by": null,
  "approved_at": null,
  "published_by": null,
  "published_at": null,
  "archived_at": null,
  "ai_provider": null,
  "ai_model": null,
  "ai_request_id": null,
  "created_at": "iso",
  "updated_at": "iso"
}
```

`MinuteListResponse`: `{ items: [MinuteResponse], total, page, page_size, pages }`.

## Errors

| Code | HTTP | Meaning |
|---|---|---|
| `MINUTE_NOT_FOUND` | 404 | minute absent or foreign tenant |
| `MEETING_NOT_FOUND` | 404 | meeting absent or foreign tenant |
| `MINUTE_INVALID_STATE` | 409 | out-of-order lifecycle transition |
| `NO_ACTIVE_MEMBERSHIP` | 403 | no active tenant membership |
| `Insufficient permissions` | 403 | missing `minutes.*` permission |
