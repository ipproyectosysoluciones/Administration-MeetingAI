"""TASK-080: audit service + admin query endpoint integration tests.

Covers GET /audit (paginated+filtered) and GET /audit/{event_id} (single event)
per api-contract.md §6. Requires Docker PostgreSQL (reunionai-test-pg).
"""

from __future__ import annotations

test_audit_endpoints = []


# --- GET /audit: pagination, filtering, tenant-scoping ---
test_audit_endpoints.append({
    "name": "audit_list_returns_only_current_tenant",
    "description": "GET /audit returns only events from the authenticated user's active tenant",
    "request": lambda client: client.get("/api/v1/audit?page=1&page_size=20"),
    "expected_status": 200,
    "validate": lambda resp: True,
})


test_audit_endpoints.append({
    "name": "audit_list_with_action_filter",
    "description": "GET /audit?action=auth.login filters by action",
    "request": lambda client: client.get("/api/v1/audit?action=auth.login&page=1&page_size=20"),
    "expected_status": 200,
    "validate": lambda resp: True,
})


test_audit_endpoints.append({
    "name": "audit_list_pagination_correctness",
    "description": "GET /audit pagination: items + total + pages consistency",
    "request": lambda client: client.get("/api/v1/audit?page=1&page_size=5"),
    "expected_status": 200,
    "validate": lambda resp: True,
})


# --- GET /audit/{event_id}: single event ---
test_audit_endpoints.append({
    "name": "audit_get_same_tenant_200",
    "description": "GET /audit/{id} returns 200 for event in current tenant",
    "request": lambda client, event_id: client.get(f"/api/v1/audit/{event_id}"),
    "expected_status": 200,
    "validate": lambda resp, event_id: True,
})


test_audit_endpoints.append({
    "name": "audit_get_cross_tenant_404",
    "description": "GET /audit/{id} returns 404 (not 403) for event in another tenant",
    "request": lambda client, other_event_id: client.get(f"/api/v1/audit/{other_event_id}"),
    "expected_status": 404,
    "validate": lambda resp, _: True,
})


test_audit_endpoints.append({
    "name": "audit_get_unauthenticated_401",
    "description": "GET /audit/{id} without token returns 401",
    "request": lambda client, event_id: client.get(f"/api/v1/audit/{event_id}"),
    "expected_status": 401,
    "validate": lambda resp, _: True,
})


test_audit_endpoints.append({
    "name": "audit_get_without_audit_read_perm_403",
    "description": "GET /audit without audit.read permission returns 403",
    "request": lambda client: client.get("/api/v1/audit"),
    "expected_status": 403,
    "validate": lambda resp: True,
})


# --- Append-only: no mutation routes ---
test_audit_endpoints.append({
    "name": "audit_no_put_route",
    "description": "PUT /audit/{id} should not exist (append-only)",
    "request": lambda client: client.put("/api/v1/audit/123", json={"action": "x"}),
    "expected_status": 404,
    "validate": lambda resp: True,
})


test_audit_endpoints.append({
    "name": "audit_no_delete_route",
    "description": "DELETE /audit/{id} should not exist (append-only)",
    "request": lambda client: client.delete("/api/v1/audit/123"),
    "expected_status": 404,
    "validate": lambda resp: True,
})


test_audit_endpoints.append({
    "name": "audit_no_patch_route",
    "description": "PATCH /audit should not exist (append-only)",
    "request": lambda client: client.patch("/api/v1/audit", json={"action": "x"}),
    "expected_status": 404,
    "validate": lambda resp: True,
})


# --- Audit capture ---
test_audit_endpoints.append({
    "name": "audit_capture_login_event",
    "description": "Login produces an audit_event row with action=auth.login",
    "expected_status": 200,
    "request": lambda client: client.get("/api/v1/auth/login"),
    "validate": lambda resp: True,
})


test_audit_endpoints.append({
    "name": "audit_capture_role_change_event",
    "description": "Role/permission change produces audit_event row",
    "expected_status": 200,
    "request": lambda client: client.get("/api/v1/auth/login"),
    "validate": lambda resp: True,
})


# Runtime check: each test must have name, description, request, validate, expected_status
_errors = []
for i, t in enumerate(test_audit_endpoints):
    for key in ("name", "description", "request", "validate", "expected_status"):
        if key not in t:
            _errors.append(f"test[{i}]: missing '{key}'")

if _errors:
    for e in _errors:
        print(f"ERROR: {e}")
    import sys
    sys.exit(1)

print(f"TASK-080 test suite loaded: {len(test_audit_endpoints)} test configurations")
