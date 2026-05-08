# Quick Start

Use the simplified Upload Studio workflow.

```bash
uv sync
cd upload-studio && npm install
cd ..
uv run python scripts/init_database.py
uv run python scripts/start_all.py
```

Open `http://localhost:5173`.

Backend API: `http://localhost:8000`.
