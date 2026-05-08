# Upload Studio Quick Start

AIOCC is now centered on a flat-file upload workflow.

## Run The Stack

```bash
uv run python scripts/init_database.py
uv run python scripts/start_all.py
```

The backend runs on `http://localhost:8000`.
The upload studio UI runs on `http://localhost:5173`.

## Workflow

1. Open the upload studio.
2. Drop a gameplay clip or browse for a file.
3. Regenerate or edit the AI metadata.
4. Choose YouTube, Instagram, TikTok, or any combination.
5. Choose visibility.
6. Upload to the selected platforms.
7. Review the recent upload results.

## Active Surface

- Frontend: `upload-studio/`
- Backend API: `backend/src/main.py`
- Studio routes: `backend/src/api/studio.py`
- Studio models: `backend/src/models/studio.py`

The active product surface is the browser upload studio and FastAPI backend.
