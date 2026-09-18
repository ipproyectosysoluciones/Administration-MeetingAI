# tenant-isolation Specification

## Purpose

Cross-cutting guarantee that Tenant A can never access Tenant B's data. This domain defines how the effective tenant is derived from the authenticated context, the validation chain that runs on every operation, and the IDOR-prevention rules all tenant-scoped modules MUST follow.

*Traceability: PRD-ReunionAI.md §6 (Modelo multi-tenant), §9 (protección contra IDOR).*

## Requirements

### Requirement: Tenant derivation from authenticated context

The system MUST derive the effective `tenant_id` solely from the authenticated user's active membership — never from any request-supplied value (path, query, header, or body). The derived tenant MUST be injected into request state (e.g., `request.state.tenant_id`) and made available through a dependency that all repositories use.

#### Scenario: Tenant derived from membership

- GIVEN an authenticated user with an active membership in organization A
- WHEN a request is authorized
- THEN the effective tenant resolves to organization A from the membership, not from any client-provided `tenant_id`

#### Scenario: Client-supplied tenant ignored

- GIVEN a request that includes a `tenant_id` pointing to a different organization in its body or parameters
- WHEN the request is processed
- THEN the client-supplied value has no effect on the effective tenant used for data access

### Requirement: Validation chain

The system MUST validate, on every operation, the chain:

```text
authenticated user → memberships → tenant → role → permission → resource ownership
```

Each link MUST be verified before granting access to any tenant-scoped resource.

#### Scenario: Full chain verified

- GIVEN an authenticated user requesting a tenant-scoped resource
- WHEN the operation is processed
- THEN the user's membership determines the tenant, their roles determine permissions, and resource ownership within the tenant is verified before access

### Requirement: tenant_id on every tenant-scoped table

Every tenant-scoped table MUST include a `tenant_id` column with an index and appropriate foreign key, and all queries against such tables MUST filter by the effective tenant from context.

#### Scenario: Repository enforces tenant filter

- GIVEN a repository query for a tenant-scoped entity
- WHEN the query is constructed
- THEN the query includes a filter on the effective `tenant_id` from context

### Requirement: IDOR prevention (Tenant A never accesses Tenant B)

The system MUST guarantee that a user in tenant A cannot read, modify, or delete any resource (users, organizations, properties, roles, memberships, audit events, or any future tenant-scoped resource) belonging to tenant B. Cross-tenant access MUST return 404 (not 403) to avoid revealing resource existence. This guarantee MUST be verified by automated integration tests for every tenant-scoped endpoint.

#### Scenario: Cross-tenant read prevented

- GIVEN a user in tenant A requesting a resource owned by tenant B
- WHEN the request is made through a tenant-scoped endpoint
- THEN the system returns 404 and discloses nothing about tenant B's resource

#### Scenario: Cross-tenant write prevented

- GIVEN a user in tenant A attempting to update or delete a resource owned by tenant B
- WHEN the request is made
- THEN the system returns 404 and performs no mutation

#### Scenario: Cross-tenant list filtered

- GIVEN a user in tenant A listing a tenant-scoped collection
- WHEN the request is made
- THEN the returned results contain only tenant A entities

#### Scenario: IDOR tests enforced

- GIVEN the automated test suite
- WHEN the suite runs
- THEN dedicated Tenant A vs Tenant B isolation tests execute for every tenant-scoped endpoint and fail the build on regression

## Acceptance Criteria

- [ ] Effective `tenant_id` derives only from the authenticated user's membership; request-supplied `tenant_id` is ignored.
- [ ] The validation chain (user → membership → tenant → role → permission → resource) runs on every operation.
- [ ] Every tenant-scoped table has an indexed `tenant_id` and all queries filter by the effective tenant.
- [ ] Tenant A can never read, write, or enumerate Tenant B resources; cross-tenant access returns 404.
- [ ] Automated IDOR integration tests cover every tenant-scoped endpoint and are blockers in CI.
