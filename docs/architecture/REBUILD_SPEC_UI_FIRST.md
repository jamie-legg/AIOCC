# AIOCC Upload Studio Specification

AIOCC is now a browser-based upload studio for manual clip uploads, AI metadata, and immediate publishing to connected platforms.

## Product Shape

The primary flow is:

1. User opens the upload studio in a browser.
2. User connects or verifies YouTube, Instagram, and TikTok.
3. User drops or browses for a gameplay clip.
4. The backend generates AI metadata from the selected file context.
5. User edits title, description, hashtags, visibility, and selected platforms.
6. User uploads immediately.
7. The UI shows recent per-platform upload results and failed-upload retry actions.

## Active Components

- `upload-studio/`: Vite, React, TypeScript, and Tailwind frontend.
- `backend/src/main.py`: Canonical FastAPI app.
- `backend/src/api/studio.py`: Upload Studio status, metadata, upload, retry, auth-start, and recent-upload routes.
- `backend/src/models/studio.py`: `UploadedClip` and `PlatformUpload` records.
- `src/managers/oauth_manager.py`: Platform OAuth token loading and refresh support.
- `src/managers/upload_manager.py`: Immediate upload orchestration for selected platforms.
- `src/platform_uploaders/`: YouTube, Instagram, and TikTok publishing adapters.
- `src/content_creation/video_processor.py`: Server-side video validation and platform optimization only.
- `scripts/start_all.py` and `scripts/start_all.ps1`: Local development startup.

## Product Boundary

The active app is only the web upload flow. Legacy local automation, desktop UI, and analytics-dashboard surfaces are outside the product boundary.

## UI Requirements

- Dark shell with AIOCC logo, authenticated badge, and user profile affordance.
- Three connected-platform cards across the top.
- Left panel with drop zone, video preview, file metadata, and platform selector.
- Right panel with AI metadata editor, visibility control, upload CTA, and recent uploads.
- Failed recent uploads show retry controls.

## API Contract

- `GET /api/v1/studio/status`
- `POST /api/v1/studio/auth/{platform}/start`
- `POST /api/v1/studio/metadata`
- `POST /api/v1/studio/upload`
- `POST /api/v1/studio/uploads/{upload_id}/retry`
- `GET /api/v1/studio/recent-uploads`
- `GET /api/v1/studio/health`

The upload endpoint accepts multipart form data:

- `video`: selected video file.
- `title`
- `description`
- `hashtags`
- `visibility`: `public`, `unlisted`, or `private`.
- `platforms`: JSON array of selected platforms.

## Runtime Model

The backend stores uploaded source files under `STUDIO_UPLOAD_DIR`, creates database records for the clip and per-platform upload attempts, and publishes immediately to the selected platforms. The frontend is a static Vite build served by nginx in production, with `/api/` and `/uploads/` proxied to FastAPI.

`docs/INDEX.md` is absent in this repo; `docs/README.md` is the documentation hub.
