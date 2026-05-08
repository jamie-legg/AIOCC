# Backend

The backend is the canonical FastAPI app for Upload Studio.

Run it with:

```bash
uv run python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000
```

## Active Routes

- `GET /health`
- `GET /api/v1/studio/status`
- `POST /api/v1/studio/metadata`
- `POST /api/v1/studio/upload`
- `GET /api/v1/studio/recent-uploads`
- `GET /api/v1/studio/health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/oauth/{platform}/initiate`

## Database

Create tables with:

```bash
uv run python scripts/init_database.py
```

The Upload Studio models live in `backend/src/models/studio.py`.
