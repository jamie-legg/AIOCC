# auth.syn.gl Upgrade Roadmap

## Phase 0 - Stabilize Existing Host

- Keep `auth-syn-gl.service` running on `127.0.0.1:3020`.
- Keep nginx and Let's Encrypt configured for `https://auth.syn.gl`.
- Keep Upload Studio registered as `upload-studio`.
- Rotate any old default credentials and secrets.
- Treat `/data/auth` as production runtime state, not open-source source of truth.

## Phase 1 - Secure OAuth2 Provider

- Remove all source-level fallback secrets.
- Require explicit `JWT_SECRET`, `SESSION_SECRET`, and database URL.
- Replace in-memory session store with SQLite/Postgres-backed sessions.
- Store OAuth client secrets hashed, not plaintext.
- Store authorization codes hashed with short TTL.
- Add refresh token rotation.
- Add token revocation.
- Add CSRF protection for login and authorization forms.
- Add brute-force protection for login attempts.

## Phase 2 - Proper OIDC

- Decide whether to support OAuth2 only or full OIDC.
- If OIDC:
  - Generate and persist signing keys.
  - Serve a real JWKS from `/.well-known/jwks.json`.
  - Issue `id_token` values.
  - Align `id_token_signing_alg_values_supported` with actual signing.
- If OAuth2 only:
  - Remove OIDC claims from discovery docs.
  - Document `/oauth/userinfo` as a profile endpoint.

## Phase 3 - User, Role, And Grant Model

- Add first-class roles:
  - `owner`
  - `admin`
  - `creator`
  - `viewer`
- Add project-level grants:
  - `upload:connect_platforms`
  - `upload:publish`
  - `upload:view_all`
  - `translations:transcribe`
  - `translations:translate`
  - `story:generate`
  - `billing:manage`
  - `users:manage`
- Allow one user to have different grants per project.
- Add team/org support later if needed.

## Phase 4 - AI Usage And Monetisation

- Track usage events:
  - user id
  - project id
  - model/provider
  - operation type
  - input units
  - output units
  - estimated cost
  - timestamp
- Add quotas and limits by plan.
- Add Stripe customer/subscription links.
- Add admin reports for spend, users, and project activity.

## Phase 5 - Admin Product

- Account dashboard at `auth.syn.gl`.
- User management.
- OAuth client management.
- Role/grant management.
- Usage dashboard.
- Audit log viewer.
- Secret/client rotation flows.

## Phase 6 - Migrate Products

- `upload.syn.gl`: replace app-local JWT RBAC with `auth.syn.gl` roles/grants.
- `translations.syn.gl`: add SSO and usage reporting.
- `story.syn.gl`: add SSO and usage reporting.
- `syn.gl`: show signed-in account state and project links.

## Production Migration Checklist

- Export legacy `/data/auth/auth.db`.
- Migrate users and clients into the new schema.
- Re-register clients with exact redirect URIs.
- Rotate old default client secrets.
- Verify `auth.syn.gl` health/discovery/token/userinfo.
- Verify each product can sign in and enforce grants.
- Keep local app fallback auth disabled after migration.
