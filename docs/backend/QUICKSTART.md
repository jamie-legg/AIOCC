# Backend Quick Start

```bash
uv sync
uv run python scripts/init_database.py
uv run python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for Swagger UI.

The frontend expects the backend at `VITE_API_BASE_URL`, defaulting to `http://localhost:8000`.
