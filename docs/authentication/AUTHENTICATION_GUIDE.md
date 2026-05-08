# Authentication

Upload Studio keeps authentication focused on the web upload workflow.

## Current State

- Backend account primitives for JWT sessions and API keys.
- Upload Studio production access can be locked with `STUDIO_ADMIN_TOKEN` and `STUDIO_USER_TOKENS`.
- OAuth credential storage for YouTube, Instagram, and TikTok.
- Platform connect/re-auth flows started from `POST /api/v1/studio/auth/{platform}/start`.
- Hosted callbacks at `/api/oauth/{platform}/callback`.
- Upload Studio status from `GET /api/v1/studio/status`, including connected platform state.

The current Upload Studio screen uses a local studio user for upload records. Full account gating can be added around the existing `/api/v1/studio/*` routes without changing the web upload workflow.

Auth is web-native for the deployed Upload Studio flow: the browser requests a provider authorization URL, the provider redirects back to FastAPI, and tokens stay server-side. The backend currently stores tokens in the server user's `.content_creation` directory; moving that storage into the database is the next hardening step.

## Production Environment

Use server-side environment variables only. Never commit real values.

```bash
BACKEND_URL=https://upload.syn.gl
OAUTH_REDIRECT_BASE_URL=https://upload.syn.gl
ALLOWED_ORIGINS=https://upload.syn.gl
STUDIO_PUBLIC_BASE_URL=https://upload.syn.gl
VITE_API_BASE_URL=https://upload.syn.gl
STUDIO_ADMIN_TOKEN=<generate-a-long-random-value>
STUDIO_USER_TOKENS=<comma-separated-alpha-user-tokens>
```

Platform credentials:

```bash
YOUTUBE_CLIENT_SECRETS_FILE=/path/to/google-client.json
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REDIRECT_URI=https://upload.syn.gl/api/oauth/youtube/callback

INSTAGRAM_CLIENT_ID=
INSTAGRAM_CLIENT_SECRET=
INSTAGRAM_REDIRECT_URI=https://upload.syn.gl/api/oauth/instagram/callback

TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_REDIRECT_URI=https://upload.syn.gl/api/oauth/tiktok/callback
```

## Authorized Redirect URIs

Register these callback URLs in the provider consoles:

```text
https://upload.syn.gl/api/oauth/youtube/callback
https://upload.syn.gl/api/oauth/instagram/callback
https://upload.syn.gl/api/oauth/tiktok/callback
```

Also keep local development/ngrok callback URLs registered only when actively developing OAuth locally.

### YouTube / Google Cloud

In Google Cloud Console:

- App type: Web application for the deployed app.
- Authorized JavaScript origins:

```text
https://upload.syn.gl
```

- Authorized redirect URIs:

```text
https://upload.syn.gl/api/oauth/youtube/callback
```

Required API/scopes:

- Enable YouTube Data API v3.
- Request `https://www.googleapis.com/auth/youtube.upload`.
- Request `https://www.googleapis.com/auth/youtube.force-ssl`.
- Request `https://www.googleapis.com/auth/youtube.readonly` if status/channel lookup is needed.

### Instagram / Meta

In Meta Developers:

- Product: Instagram API with Instagram Login / Business Login as configured for the app.
- Valid OAuth Redirect URIs:

```text
https://upload.syn.gl/api/oauth/instagram/callback
```

Required permissions for the current uploader:

```text
instagram_business_basic
instagram_business_content_publish
```

Add `instagram_business_manage_insights` only if analytics/status features need it.

### TikTok

In TikTok for Developers:

- Redirect URI:

```text
https://upload.syn.gl/api/oauth/tiktok/callback
```

Required scopes for upload and account status:

```text
user.info.profile
user.info.stats
video.upload
video.publish
video.list
```

## Token Storage Target

The current hosted browser/callback flow is in place. The next cleanup should move token persistence from file storage to database-backed storage:

1. Store tokens in the `OAuthCredential` model.
2. Encrypt token values at rest.
3. Keep the frontend token-free.
4. Keep provider client secrets in server environment or a secret manager only.

## RBAC Target

The immediate production lock has two token roles:

1. Admin token: can connect/reconnect platform OAuth, generate metadata, upload, retry, and view studio status/history.
2. Alpha user tokens: can generate metadata, upload, retry, and view studio status/history after an admin connects platforms. They cannot start platform OAuth.

A fuller RBAC system should add:

1. `admin` users who can connect platform accounts, review all uploads, retry failures, and manage users.
2. `creator` users who can upload clips and view their own upload history.
3. `viewer` users who can only view status/history.
4. Per-user upload records and audit logs for metadata generation, platform auth, upload attempts, retries, and failures.
5. Admin screens for user status, quotas, connected account health, and recent upload outcomes.

## Production Notes

- Set a strong `SECRET_KEY`.
- Restrict `ALLOWED_ORIGINS` to the deployed origin.
- Serve the app over HTTPS.
- Keep OAuth client secrets and token files out of Git.
- Re-authenticate a platform from the Upload Studio platform cards when its token expires or is revoked.
