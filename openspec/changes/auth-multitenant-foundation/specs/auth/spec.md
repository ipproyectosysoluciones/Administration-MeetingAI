# auth Specification

## Purpose

Authentication and session security for ReunionAI. This domain owns registration, login, token issuance/refresh/rotation, token revocation, MFA enrollment and verification (TOTP), session listing and revocation, and rate limiting on authentication endpoints. It is the entry point for establishing an authenticated principal and issuing credentials, but it MUST NOT itself decide tenant scoping or authorization (see `tenant-isolation` and `rbac` domains).

*Traceability: PRD-ReunionAI.md §7 (Usuarios/roles), §9 (Seguridad: hashing, access tokens con expiración, refresh tokens con rotación, MFA/2FA, control de sesiones, rate limiting).*

## Requirements

### Requirement: Self-service registration creates an organization and its org-admin

The system MUST provide a registration flow that creates a new tenant organization together with its first Organization Admin user, links them via a membership, hashes the password, and returns valid access and refresh tokens on success.

Registration MUST NOT create platform-level Super Admin accounts. The first Super Admin MUST be created only through a CLI bootstrap script (`Q1`).

The system MUST reject registration when the email already exists globally (including soft-deleted users).

#### Scenario: Successful self-service registration

- GIVEN an unregistered email and valid organization/user payload
- WHEN the client submits `POST /auth/register`
- THEN the system creates an `Organization`, a `User` with role Organization Admin, a `Membership` linking them, and returns a valid access token and refresh token

#### Scenario: Duplicate email rejected

- GIVEN an email that already exists (active or soft-deleted)
- WHEN the client submits `POST /auth/register`
- THEN the system returns 409 Conflict and creates no new organization or user

#### Scenario: Platform super-admin cannot self-register

- GIVEN a client attempting to claim the Super Admin role
- WHEN the client submits `POST /auth/register` requesting a platform-level role
- THEN the system rejects the request; Super Admin creation is only possible via the CLI bootstrap script

### Requirement: Super-admin bootstrap

The system MUST provide a CLI bootstrap script that creates the first platform-level Super Admin account. The script MUST require configuration via environment variables and MUST NOT depend on self-service registration.

#### Scenario: Bootstrap creates first super-admin idempotently

- GIVEN an empty system with no platform Super Admin
- WHEN the bootstrap script runs with a configured email and password
- THEN exactly one Super Admin user is created; re-running with the same email does not create a duplicate

### Requirement: Login

The system MUST authenticate a user by email and password, using a password verifier against the stored password hash. On successful authentication, if MFA is not enabled for the user, the system MUST return an access token and a refresh token. If MFA is enabled, the system MUST return a partial (MFA-pending) response rather than full tokens and require an MFA challenge before issuing tokens.

#### Scenario: Successful login without MFA

- GIVEN an active user with a correct password and MFA not enabled
- WHEN the client submits `POST /auth/login`
- THEN the system returns a valid access token (15-minute TTL) and a rotating refresh token (30-day TTL)

#### Scenario: Wrong password rejected

- GIVEN an active user
- WHEN the client submits `POST /auth/login` with an incorrect password
- THEN the system returns 401 Unauthorized and issues no tokens

#### Scenario: MFA-enabled user requires challenge

- GIVEN an active user with MFA enabled
- WHEN the client submits `POST /auth/login` with correct credentials
- THEN the system returns an MFA-pending response and issues no access/refresh tokens until the MFA challenge succeeds

### Requirement: Access token issuance

The system MUST issue access tokens as JWTs signed with RS256, with a TTL of 15 minutes, carrying `user_id`, `tenant_id`, and resolved `permissions` claims that the backend verifies on every authenticated request.

#### Scenario: Valid token carries required claims

- GIVEN a successful authentication event
- WHEN the system issues an access token
- THEN the token is an RS256 JWT with a 15-minute `exp`, and includes `user_id`, `tenant_id`, and `permissions` claims

#### Scenario: Expired token rejected

- GIVEN an access token past its `exp`
- WHEN the client presents the token on an authenticated endpoint
- THEN the system returns 401 Unauthorized

### Requirement: Refresh token issuance and rotation

The system MUST issue refresh tokens that are stored hashed (never in plaintext) in the database, have a 30-day TTL, and rotate on every use: a valid refresh produces a new refresh token and invalidates the presented one, linked through a rotation chain (`replaced_by_token_id`).

#### Scenario: Successful rotation

- GIVEN a valid, unexpired, unused refresh token
- WHEN the client submits `POST /auth/refresh`
- THEN the system issues a fresh access token and a new refresh token, and marks the presented token as replaced

### Requirement: Refresh token reuse detection

The system MUST detect reuse of an already-used (replaced or revoked) refresh token and, on detection, MUST revoke the entire token chain for that user and require re-authentication.

#### Scenario: Replayed refresh token revokes the chain

- GIVEN a refresh token that was already used to rotate once and a live sibling token from the same chain
- WHEN a client presents the already-used token to `POST /auth/refresh`
- THEN the system detects reuse, revokes the entire chain (including the sibling token), and rejects the request

#### Scenario: Grace window for concurrent refresh

- GIVEN two near-simultaneous refresh requests using tokens from the same chain
- WHEN they arrive within the configured grace window (30 seconds)
- THEN the system permits the legitimate successor token to succeed while still flagging true reuse outside the window

### Requirement: Token revocation (logout)

The system MUST allow an authenticated user to revoke their current refresh token, ending that session.

#### Scenario: Logout revokes current refresh token

- GIVEN an authenticated user with an active refresh token
- WHEN the client submits `POST /auth/revoke`
- THEN the system revokes the current refresh token and subsequent refresh with that token fails

### Requirement: MFA enrollment (TOTP)

The system MUST support TOTP (RFC 6238) MFA enrollment, returning a secret and QR code provisioning URI when the authenticated user requests setup, and verifying a TOTP code before enabling MFA. MFA enrollment MUST be authorized by the `user.mfa.manage` permission.

#### Scenario: Setup returns provisioning secret

- GIVEN an authenticated user with `user.mfa.manage` permission
- WHEN the client submits `POST /auth/mfa/setup`
- THEN the system returns a TOTP secret and otpauth provisioning URI (QR code)

#### Scenario: Enrollment requires verification

- GIVEN an authenticated user who has completed setup but not verified
- WHEN the client submits `POST /auth/mfa/verify` with a correct TOTP code
- THEN the system enables MFA for the user; an incorrect code rejects enablement

### Requirement: MFA challenge during login

The system MUST verify a TOTP code as the second factor for MFA-enabled users during login, and only then issue access and refresh tokens. Incorrect TOTP codes MUST be rejected and MFA challenge attempts MUST be rate-limited.

#### Scenario: Successful MFA challenge

- GIVEN an MFA-enabled user with a valid MFA-pending login
- WHEN the client submits `POST /auth/mfa/challenge` with the correct TOTP code
- THEN the system issues a valid access token and refresh token

#### Scenario: Failed MFA challenge

- GIVEN an MFA-enabled user with a valid MFA-pending login
- WHEN the client submits an incorrect TOTP code
- THEN the system returns 401 and issues no tokens

### Requirement: MFA mandatory for administrative roles

The system MUST require MFA for the Super Admin, Organization Admin, and Property Admin roles. MFA MUST be optional for all other roles in this change; organization-level MFA policy configuration is deferred to a later change (`Q3`).

#### Scenario: Admin without MFA cannot complete privileged login

- GIVEN a user holding Super Admin, Organization Admin, or Property Admin role and MFA not yet enabled
- WHEN that user performs login
- THEN the system requires MFA enrollment before (or as part of) granting privileged access, per the mandated policy

#### Scenario: Non-admin may log in without MFA

- GIVEN a user holding a non-administrative role (e.g., Co-owner, Resident)
- WHEN that user performs login without MFA enabled
- THEN the system permits password-only login

### Requirement: MFA disable

The system MUST allow MFA to be disabled only with password confirmation, authorized by `user.mfa.manage`.

#### Scenario: Disable requires password confirmation

- GIVEN an MFA-enabled user with `user.mfa.manage`
- WHEN the client submits `POST /auth/mfa/disable` with the correct password
- THEN MFA is disabled; an incorrect password does not disable MFA

### Requirement: Session listing and revocation

The system MUST allow a user to list all their active sessions across devices and revoke any or all of them (`Q4`). Revocation MUST invalidate the corresponding refresh token and its access session.

#### Scenario: List all sessions

- GIVEN a user with sessions on multiple devices
- WHEN the client submits `GET /users/me/sessions`
- THEN the system returns all active sessions for that user

#### Scenario: Revoke one session

- GIVEN a user with multiple active sessions
- WHEN the client submits `DELETE /users/me/sessions/{id}` for one session
- THEN only that session's refresh token is revoked; other sessions remain valid

### Requirement: Rate limiting on authentication endpoints

The system MUST apply rate limiting to authentication endpoints (login, register, refresh, MFA challenge). Implementation MUST use in-memory rate limiting for this change (no Redis, per `Q5`), with a documented migration path to Redis for multi-worker deployment. Rate limits MUST be enforced per-IP and per-user.

#### Scenario: Rate limit enforced per IP

- GIVEN a client exceeding the configured per-IP threshold on `POST /auth/login`
- WHEN the client makes further login attempts
- THEN the system returns 429 Too Many Requests until the window resets

#### Scenario: Rate limit enforced per user

- GIVEN a specific user account being targeted
- WHEN login/refresh attempts exceed the per-user threshold
- THEN the system returns 429 and does not process the attempts

### Requirement: Secure password hashing

The system MUST hash passwords with Argon2id (via `passlib[argon2]`) and MUST never store or log plaintext passwords. Verification MUST use a constant-time verifier.

#### Scenario: Plaintext never persisted

- GIVEN a registered or onboarding user with a password
- WHEN the password is stored
- THEN the database contains only an Argon2id hash; the plaintext is absent from storage and logs

## Acceptance Criteria

- [ ] `POST /auth/register` creates an org, an Organization Admin user, and a membership, and returns valid tokens.
- [ ] Registration cannot create a platform Super Admin; a CLI bootstrap script is the only path to the first Super Admin.
- [ ] `POST /auth/login` issues an RS256 JWT (15-minute TTL) plus a rotating refresh token (30-day TTL).
- [ ] MFA-pending login path issues tokens only after a successful TOTP challenge.
- [ ] `POST /auth/refresh` rotates the refresh token; presenting a used token revokes the entire chain.
- [ ] MFA is mandatory for Super Admin, Organization Admin, and Property Admin; optional otherwise.
- [ ] `GET /users/me/sessions` lists all sessions and per-session revocation works.
- [ ] Auth endpoints enforce per-IP and per-user in-memory rate limiting returning 429 on exceedance.
- [ ] Passwords are Argon2id-hashed; plaintext never appears in storage or logs.
