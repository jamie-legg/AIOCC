# Authentication

Upload Studio keeps authentication focused on the web upload workflow.

## Current State

- Backend account primitives for JWT sessions and API keys.
- Upload Studio production access uses username/password login, JWTs, and roles.
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
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=<generate-a-long-random-value>
ALLOW_PUBLIC_REGISTRATION=false
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

## RBAC

Upload Studio uses three roles:

1. `admin`: can connect platform accounts, generate metadata, upload, retry, view all upload history, and create users.
2. `creator`: can generate metadata, upload, retry their own uploads, and view their own upload history after an admin connects platforms.
3. `viewer`: can sign in and view status/history, but cannot publish clips or connect platforms.

The current admin UI includes user creation and upload-count monitoring. The next iteration should add richer audit logs, per-user quotas, user disable/reset controls, and encrypted database-backed OAuth token storage.

## syn.gl SSO

`auth.syn.gl` is the shared identity service for syn.gl projects. Upload Studio is registered as an OAuth client:

```bash
AUTH_SYN_BASE_URL=https://auth.syn.gl
AUTH_SYN_CLIENT_ID=upload-studio
AUTH_SYN_CLIENT_SECRET=<server-only-client-secret>
AUTH_SYN_REDIRECT_URI=https://upload.syn.gl/auth/callback
AUTH_SYN_DEFAULT_ROLE=creator
```

The login screen uses `Continue with syn.gl` as the primary path. Local username/password login remains as a fallback while auth.syn.gl matures.

The Upload Studio OAuth client registered in `/data/auth/auth.db` uses:

```text
client_id: upload-studio
redirect_uri: https://upload.syn.gl/auth/callback
```

## Production Notes

- Set a strong `SECRET_KEY`.
- Restrict `ALLOWED_ORIGINS` to the deployed origin.
- Serve the app over HTTPS.
- Keep OAuth client secrets and token files out of Git.
- Re-authenticate a platform from the Upload Studio platform cards when its token expires or is revoked.
