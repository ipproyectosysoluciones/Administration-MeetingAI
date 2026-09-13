# organizations Specification

## Purpose

Tenant organization lifecycle, property/group (sub-tenant) lifecycle, and membership management. An organization is the primary multi-tenant boundary; properties/groups are optional subdivisions within it. Membership links a user to an organization and, optionally, to a property/group (`Q2`).

*Traceability: PRD-ReunionAI.md §6 (Modelo multi-tenant: Platform → Organization → Property/Group → Users).*

## Requirements

### Requirement: Organization creation

The system MUST support organization creation authorized by `organization.create`. For self-service flow, `POST /auth/register` creates the organization and first admin in one transaction (see `auth`). For an additional organization after registration, creation MUST require the `organization.create` permission (Super Admin only in this change).

#### Scenario: Self-service creates organization

- GIVEN a registration request
- WHEN the client submits `POST /auth/register`
- THEN an organization is created with the registering user as Organization Admin

#### Scenario: Super-admin creates additional organization

- GIVEN an authenticated Super Admin with `organization.create`
- WHEN the client submits `POST /organizations`
- THEN a new organization is created

### Requirement: Organization read/update

The system MUST allow the current user to read (`organization.read`) and update (`organization.update`) their own organization via tenant-scoped paths (`/organizations/me`).

#### Scenario: Update own organization settings

- GIVEN an authenticated user in tenant A with `organization.update`
- WHEN the client submits `PATCH /organizations/me`
- THEN the system updates the current organization's settings

### Requirement: Organization soft delete

The system MUST soft-delete organizations (set `deleted_at`) rather than hard-delete, cascading soft-delete to their memberships.

#### Scenario: Soft delete cascades to memberships

- GIVEN an organization with members
- WHEN the organization is soft-deleted by an authorized actor
- THEN its memberships are soft-deleted and its users lose tenant access

### Requirement: Property/Group CRUD

The system MUST support create, read, list, update, and delete of properties/groups within the current organization, authorized by `property.create`, `property.read`, `property.update`, and `property.delete` respectively, all scoped to the current tenant.

#### Scenario: Create property within tenant

- GIVEN an authorized actor in tenant A with `property.create`
- WHEN the client submits `POST /organizations/me/properties`
- THEN a property/group is created under tenant A's organization

#### Scenario: Cross-tenant property access denied

- GIVEN an actor in tenant A referencing a property that belongs to tenant B
- WHEN the client submits `PATCH /organizations/me/properties/{id}` or `DELETE /organizations/me/properties/{id}`
- THEN the system returns 404 and performs no operation

### Requirement: Membership management

The system MUST support listing, creating (invite/add), updating, and removing organization memberships, authorized by `membership.read`, `membership.create`, `membership.update`, and `membership.delete` respectively, scoped to the current tenant.

#### Scenario: Add a member

- GIVEN an authorized actor in tenant A with `membership.create`
- WHEN the client submits `POST /organizations/me/memberships`
- THEN a membership is created for the target user in tenant A

#### Scenario: Assign membership to a property

- GIVEN an authorized actor and an existing property in tenant A
- WHEN the client creates a membership referencing that property
- THEN the membership records the `property_id`

#### Scenario: Optional property on membership

- GIVEN an authorized actor creating a direct organization membership
- WHEN the membership is created without a property
- THEN `property_id` is `null` and the membership remains valid (`Q2`)

#### Scenario: Remove a member

- GIVEN an authorized actor in tenant A with `membership.delete`
- WHEN the client submits `DELETE /organizations/me/memberships/{id}`
- THEN the membership is removed and the user loses tenant A access (unless another membership remains)

## Acceptance Criteria

- [ ] Self-service registration and Super Admin `POST /organizations` both create organizations through `organization.create`.
- [ ] `/organizations/me` read/update are tenant-scoped.
- [ ] Organization soft delete cascades to memberships.
- [ ] Property/group CRUD is fully tenant-scoped; cross-tenant property access returns 404.
- [ ] Membership supports nullable `property_id`; property-scoped and direct memberships both work.
- [ ] Membership add/update/remove are authorized and tenant-scoped.
