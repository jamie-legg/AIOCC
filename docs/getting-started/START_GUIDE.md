# Start Guide

Start everything:

```bash
uv run python scripts/start_all.py
```

Start services separately:

```bash
uv run python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000
cd upload-studio && npm run dev
```

The UI uses `VITE_API_BASE_URL` and defaults to `http://localhost:8000`.
