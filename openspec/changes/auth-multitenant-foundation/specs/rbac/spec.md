# rbac Specification

## Purpose

Role-based access control: the permission registry (`resource.action`), base and custom roles, role↔permission and user↔role assignments, and the permission resolution contract. The backend enforces every action by resolving permissions from the authenticated user's roles in the active tenant; it MUST never rely on frontend restrictions or scattered role-name checks.

*Traceability: PRD-ReunionAI.md §7 (Roles base + roles personalizados), §8 (RBAC: resources/actions, tenants, separación de privilegios, backend enforcement).*

## Requirements

### Requirement: Permission registry

The system MUST maintain a registry of permissions in the form `resource.action` (e.g., `meeting.create`, `minutes.approve`, `document.download`, `user.read`). The registry MUST be enumerable via `GET /rbac/permissions` (authorized by `permission.read`) and MUST be the single source of truth for permission names used in authorization checks.

#### Scenario: List permissions

- GIVEN an authenticated user with `permission.read`
- WHEN the client submits `GET /rbac/permissions`
- THEN the system returns the full list of `resource.action` permissions

#### Scenario: Unknown permission rejected

- GIVEN an authorization check against a permission not in the registry
- WHEN resolution occurs
- THEN the permission is treated as absent (deny) rather than granted

### Requirement: Base roles

The system MUST provide base (system) roles matching the PRD: Super Admin, Organization Admin, Property Admin, President, Secretary, Board Member, Reviewer, Co-owner, Resident, and Guest. Base roles MUST have fixed permissions, MUST NOT be deletable or modifiable by tenant users, and MUST be scoped appropriately (Super Admin is platform-scoped; Organization Admin and Property Admin are tenant-scoped).

#### Scenario: Base roles are immutable

- GIVEN a tenant-scoped actor
- WHEN the client attempts `DELETE /rbac/roles/{id}` on a base role
- THEN the system rejects the operation

#### Scenario: Base roles present at bootstrap

- GIVEN a freshly initialized system
- WHEN roles are listed
- THEN all ten base roles are defined and usable

### Requirement: Custom roles per organization

The system MUST allow each organization to create, update, and delete custom roles scoped to that organization (tenant). Custom roles MUST NOT exist or be visible outside their owning organization.

#### Scenario: Create custom role

- GIVEN an authorized actor with `role.create` in tenant A
- WHEN the client submits `POST /rbac/roles` with a name and permissions
- THEN a custom role is created under tenant A

#### Scenario: Delete custom role only

- GIVEN a custom role in tenant A
- WHEN the client submits `DELETE /rbac/roles/{id}`
- THEN a custom role is deleted; a base/system role is rejected

#### Scenario: Cross-tenant role invisible

- GIVEN a custom role owned by tenant A and an actor in tenant B
- WHEN the tenant B actor lists or modifies roles
- THEN the tenant A custom role is not returned and cannot be modified

### Requirement: Role-permission assignment

The system MUST support assigning and revoking permissions on a role via `role.permission.assign` and `role.permission.revoke`, scoped to the role's owning tenant.

#### Scenario: Assign permission to role

- GIVEN a custom role in tenant A and an authorized actor
- WHEN the client submits `POST /rbac/roles/{id}/permissions`
- THEN the permission is added to the role and included in subsequent resolution

#### Scenario: Revoke permission from role

- GIVEN a role with a permission and an authorized actor
- WHEN the client submits `DELETE /rbac/roles/{id}/permissions/{perm_id}`
- THEN the permission is removed from the role

### Requirement: User-role assignment

The system MUST support assigning and revoking roles on a user within the current tenant via `user.role.assign` and `user.role.revoke`, scoped to the tenant.

#### Scenario: Assign role to user

- GIVEN an authorized actor in tenant A and a user who is a member of tenant A
- WHEN the client submits `POST /rbac/users/{user_id}/roles`
- THEN the role is granted to the user in tenant A

#### Scenario: Revoke role from user

- GIVEN a user with a role in tenant A and an authorized actor
- WHEN the client submits `DELETE /rbac/users/{user_id}/roles/{role_id}`
- THEN the role is revoked from the user in tenant A

### Requirement: Permission resolution contract

The system MUST resolve a user's effective permissions as the union of permissions from all roles assigned to the user within the active tenant. Resolution MUST occur at the backend on every authorized request and MUST NOT be supplied or trusted from the client. Authentication tokens MAY carry a snapshot of resolved permissions as a claim, but authoritative re-resolution from the backend MUST be the enforcement source.

#### Scenario: Union of role permissions

- GIVEN a user with two roles in tenant A whose permission sets overlap
- WHEN the user's effective permissions are resolved
- THEN the result is the union of both roles' permissions

#### Scenario: Resolution is tenant-scoped

- GIVEN a user with a role in tenant A and a different role in tenant B
- WHEN permissions are resolved for tenant A
- THEN only tenant A role permissions are returned; tenant B permissions are excluded

### Requirement: Backend-enforced authorization

The system MUST enforce every protected action at the backend via a permission dependency (e.g., `@require_permission("resource.action")`) that resolves the authenticated user's permissions in the active tenant. The system MUST return 403 Forbidden when the user lacks the required permission, and 401 when unauthenticated.

#### Scenario: Authorized request succeeds

- GIVEN an authenticated user with the required permission for an endpoint
- WHEN the client invokes the endpoint
- THEN the system processes the request

#### Scenario: Unauthorized request returns 403

- GIVEN an authenticated user without the required permission
- WHEN the client invokes a protected endpoint
- THEN the system returns 403 Forbidden

#### Scenario: Never trust frontend

- GIVEN a client that attempts an action the backend has not authorized
- WHEN the client invokes the mutation endpoint directly (bypassing the frontend)
- THEN the backend denies the request regardless of any frontend controls

## Acceptance Criteria

- [ ] `GET /rbac/permissions` returns the `resource.action` registry.
- [ ] All ten PRD base roles exist, are immutable by tenants, and are correctly scoped (Super Admin platform-scoped).
- [ ] Custom roles are created/updated/deleted per organization and are tenant-isolated.
- [ ] Role↔permission and user↔role assignment/revocation endpoints work and are tenant-scoped.
- [ ] Effective permissions equal the union of a user's roles in the active tenant only.
- [ ] Protected endpoints enforce via backend dependency; 403 without permission, 401 when unauthenticated.
