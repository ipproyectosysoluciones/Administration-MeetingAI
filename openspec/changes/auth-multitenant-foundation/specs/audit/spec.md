# audit Specification

## Purpose

Append-only audit trail for critical operations. The `audit_events` table records actor, tenant, action, resource, resource_id, timestamp, ip, user_agent, and metadata for every critical mutation. Events are written automatically by middleware and are never editable or deletable through the normal API.

*Traceability: PRD-ReunionAI.md §10 (Auditoría: eventos relevantes, campos mínimos, no modificables desde la interfaz).*

## Requirements

### Requirement: Audit event schema

The system MUST persist audit events in an `audit_events` table with at minimum the fields `id` (UUID PK), `actor_user_id`, `tenant_id`, `action`, `resource`, `resource_id`, `timestamp` (TIMESTAMPTZ), `ip`, `user_agent`, and `metadata` (JSONB). `tenant_id` MUST be present and must reference the organization (tenant) that owns the event.

#### Scenario: Event carries all required fields

- GIVEN a critical operation performed by an authenticated user in a tenant
- WHEN an audit event is recorded
- THEN the event stores actor_user_id, tenant_id, action, resource, resource_id, timestamp, ip, user_agent, and metadata

### Requirement: Append-only write API

The system MUST make audit events append-only. There MUST be no update or delete path for audit events through the application or ORM, and normal UI MUST NOT be able to modify them. The backend MUST prohibit UPDATE/DELETE on `audit_events` (e.g., via revoked grants or a database-level guard).

#### Scenario: No update or delete endpoint exists

- GIVEN the audit module's exposed routes
- WHEN a client enumerates available operations
- THEN there is no update or delete operation for audit events

#### Scenario: Direct modification prevented

- GIVEN any attempt to modify an audit event through application code or SQL under the app's database role
- WHEN the attempt is made
- THEN the modification is denied

### Requirement: Critical-operation event capture

The system MUST automatically record audit events for critical operations including: login success/failure, logout, password change, MFA enable/disable/enroll, user CRUD (create/update/delete), organization CRUD, membership changes, and role/permission changes.

#### Scenario: Login and logout recorded

- GIVEN a user who logs in and later logs out
- WHEN each operation occurs
- THEN audit events exist for both login and logout with the correct action and actor

#### Scenario: RBAC change recorded

- GIVEN an authorized actor assigning or revoking a role or permission
- WHEN the change is applied
- THEN an audit event is recorded with action describing the permission/role change and the affected resource

### Requirement: Admin query endpoint

The system MUST expose a tenant-scoped, paginated, filterable query endpoint (`GET /audit`) authorized by `audit.read`, returning only the current tenant's audit events, and a detail endpoint (`GET /audit/{id}`). Events MUST be ordered by descending timestamp.

#### Scenario: Tenant-scoped audit list

- GIVEN an authorized actor in tenant A and audit events from tenants A and B
- WHEN the client submits `GET /audit`
- THEN the system returns only tenant A's events

#### Scenario: Cross-tenant audit detail denied

- GIVEN an actor in tenant A requesting an audit event that belongs to tenant B
- WHEN the client submits `GET /audit/{id}`
- THEN the system returns 404

#### Scenario: Filter and pagination

- GIVEN a large number of audit events in a tenant
- WHEN the client submits `GET /audit` with filters and pagination parameters
- THEN results are filtered, paginated, and ordered by timestamp descending

## Acceptance Criteria

- [ ] `audit_events` contains all required fields (actor, tenant, action, resource, resource_id, timestamp, ip, user_agent, metadata).
- [ ] Audit events are append-only; no update/delete path exists in app or ORM and normal UI cannot modify them.
- [ ] Events are recorded for login, logout, password change, MFA changes, user/org CRUD, membership changes, and role/permission changes.
- [ ] `GET /audit` and `GET /audit/{id}` are tenant-scoped and authorized by `audit.read`; cross-tenant access returns 404.
