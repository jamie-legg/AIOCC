# auth.syn.gl

Central identity service for the `syn.gl` project network.

`auth.syn.gl` is intended to be the shared account, authorization, and AI usage service for:

- `upload.syn.gl` - Upload Studio and platform publishing.
- `translations.syn.gl` - transcription, podcast, and document translation workflows.
- `story.syn.gl` - infinite narrative/culture engine.
- future `syn.gl` tools that need user accounts, quotas, billing, and audit trails.

## Current Status

The production host currently runs a legacy Node/Express OAuth2 service from `/data/auth`. It has been repaired enough to serve Upload Studio SSO:

- `https://auth.syn.gl/health`
- `https://auth.syn.gl/oauth/authorize`
- `https://auth.syn.gl/oauth/token`
- `https://auth.syn.gl/oauth/userinfo`

This repository module tracks the open-source replacement/hardening path. Do not copy private production secrets or databases into this directory.

## Target Responsibilities

- User accounts and profile data.
- OAuth2/OIDC provider for `syn.gl` applications.
- Project-level roles and grants.
- AI usage metering across products.
- Subscription and billing entitlements.
- API keys and personal access tokens.
- Admin audit logs.

## Initial Clients

| Client | Redirect URI | Notes |
| --- | --- | --- |
| `upload-studio` | `https://upload.syn.gl/auth/callback` | Deployed first client. |
| `translations` | `https://translations.syn.gl/auth/callback` | Planned. |
| `story` | `https://story.syn.gl/auth/callback` | Planned. |
| `syn-home` | `https://syn.gl/auth/callback` | Planned homepage/account entry. |

## Security Rules

- No default credentials.
- No fallback JWT/session/client secrets in source code.
- No committed SQLite databases.
- Production secrets live in environment or a secret manager.
- OAuth client secrets are only shown once or rotated by an admin.
- Tokens and auth codes are stored hashed where practical.
- Admin actions write audit events.

## Local Development Shape

```bash
cp .env.example .env
npm install
npm run dev
```

This module is currently a tracked design/scaffold. See `ROADMAP.md` for the migration plan before replacing the production `/data/auth` service.
