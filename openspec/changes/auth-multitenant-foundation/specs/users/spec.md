# users Specification

## Purpose

User identity, profile, password lifecycle, MFA device management, and membership representation. Users are global identities (one account, one email) that belong to organizations through memberships. This domain owns the user-scoped read/write operations and the per-user credential and device state; authorization of those operations is governed by `rbac` and scoping by `tenant-isolation`.

*Traceability: PRD-ReunionAI.md §7 (Usuarios), §9 (Seguridad: cambio de contraseña), §6 (Modelo multi-tenant: Users under Organization).*

## Requirements

### Requirement: Current user profile (self)

The system MUST return the authenticated user's profile together with their permissions resolved for the current tenant when the client requests `GET /users/me`.

#### Scenario: Self profile with resolved permissions

- GIVEN an authenticated user
- WHEN the client submits `GET /users/me`
- THEN the system returns the user's profile and the union of permissions from their roles in the active tenant

### Requirement: Profile update (self)

The system MUST allow an authenticated user to update their own profile fields (e.g., name, avatar), authorized by `user.update`, and MUST reject attempts to change fields not permitted by that operation (e.g., email, roles, tenant).

#### Scenario: Update own name

- GIVEN an authenticated user with `user.update` permission
- WHEN the client submits `PATCH /users/me` with a new name
- THEN the system updates the name and returns the updated profile

#### Scenario: Cannot self-elevate

- GIVEN an authenticated user
- WHEN the client submits `PATCH /users/me` attempting to change role or tenant assignment
- THEN the system rejects the field change

### Requirement: Password change

The system MUST allow a user to change their own password by providing the current password and a new password, authorized by `user.password.change`. The system MUST hash the new password with Argon2id and MUST record a password-change audit event (see `audit`).

#### Scenario: Change password with valid current password

- GIVEN an authenticated user with a known current password
- WHEN the client submits `POST /users/me/password` with correct current and new passwords
- THEN the password is re-hashed with Argon2id and an audit event is recorded

#### Scenario: Wrong current password rejected

- GIVEN an authenticated user
- WHEN the client submits `POST /users/me/password` with an incorrect current password
- THEN the system returns 400/401 and the password is unchanged

### Requirement: MFA device management

The system MUST allow an authenticated user to manage their own MFA devices (list, name, remove) under `user.mfa.manage`. Removal of an MFA device MUST require password confirmation.

#### Scenario: List MFA devices

- GIVEN an authenticated user with enrolled MFA devices
- WHEN the client submits `GET /users/me/mfa`
- THEN the system returns the user's MFA devices

#### Scenario: Remove MFA device requires confirmation

- GIVEN an authenticated user with an enrolled MFA device
- WHEN the client submits removal with the correct password
- THEN the device is removed; an incorrect password does not remove it

### Requirement: Memberships

The system MUST expose a user's memberships. A membership MAY be a direct organization membership without a property/group (nullable `property_id`) or MAY reference a specific property/group within the organization (`Q2`). The active tenant for context resolution derives from the user's membership (see `tenant-isolation`).

#### Scenario: Direct organization membership

- GIVEN a user who is a direct member of an organization with no property assignment
- WHEN their memberships are resolved
- THEN the membership has a `null` `property_id` and the organization is the active tenant

#### Scenario: Property-scoped membership

- GIVEN a user assigned to a specific property/group within an organization
- WHEN their memberships are resolved
- THEN the membership references the property and both organization and property are preserved

### Requirement: List users in tenant (admin)

The system MUST allow an authorized actor (with `user.read`) to list users belonging to the current tenant, and MUST return only users with a membership in that tenant.

#### Scenario: Tenant-scoped user list

- GIVEN an authorized actor in tenant A
- WHEN the client submits `GET /users`
- THEN the system returns only users with a membership in tenant A, excluding users from any other tenant

### Requirement: Get a user in tenant

The system MUST allow an authorized actor (with `user.read`) to fetch a single user by id within the current tenant, and MUST return 404 if the user has no membership in the current tenant (preventing cross-tenant enumeration/IDOR).

#### Scenario: Cross-tenant user access denied

- GIVEN an authorized actor in tenant A requesting a user who belongs only to tenant B
- WHEN the client submits `GET /users/{id}`
- THEN the system returns 404 and reveals nothing about tenant B's user

### Requirement: Update a user (admin)

The system MUST allow an authorized actor (with `user.update`) to update another user within the current tenant, scoped by tenant.

#### Scenario: Tenant-scoped admin update

- GIVEN an authorized actor in tenant A and a user who belongs to tenant A
- WHEN the client submits `PATCH /users/{id}`
- THEN the update applies; a user belonging only to tenant B cannot be updated (404)

### Requirement: Delete (soft-delete) a user

The system MUST soft-delete users (set `deleted_at`) rather than hard-delete, authorized by `user.delete`, preserving audit references. Soft-deleted users MUST NOT be able to log in and MUST NOT appear in normal user listings.

#### Scenario: Soft delete prevents login

- GIVEN an authorized actor soft-deleting a user
- WHEN the soft-deleted user attempts login
- THEN the system rejects authentication with 401

#### Scenario: Audit reference preserved

- GIVEN a user with existing audit events
- WHEN the user is soft-deleted
- THEN the audit events remain present and reference the (soft-deleted) user

## Acceptance Criteria

- [ ] `GET /users/me` returns profile plus resolved permissions for the active tenant.
- [ ] `PATCH /users/me` updates permitted profile fields and cannot change email/roles/tenant.
- [ ] Password change requires current password, re-hashes with Argon2id, and records an audit event.
- [ ] MFA device list/remove works; removal requires password confirmation.
- [ ] Membership supports nullable `property_id` (direct org membership) and property-scoped membership.
- [ ] `GET /users` and `GET /users/{id}` return only current-tenant users; cross-tenant access returns 404.
- [ ] Soft delete prevents login and preserves audit references.
