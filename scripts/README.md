# Scripts

The scripts folder supports the web Upload Studio stack.

## Active Scripts

- `start_all.py`: Starts the FastAPI backend and the `upload-studio` Vite app.
- `start_all.ps1`: PowerShell equivalent for Windows.
- `init_database.py`: Creates backend database tables from the SQLAlchemy models.
- `auth_platform.py`: Starts platform OAuth for YouTube, Instagram, or TikTok.
- `probe_instagram_container.py`: Debug helper for Instagram media container errors.
- `setup_windows.ps1` and `setup_windows.bat`: Local environment setup helpers.
- `start_ngrok_api.ps1` and `verify_ngrok.ps1`: Optional OAuth callback tunnel helpers.

## Product Boundary

AIOCC is a browser-based upload studio. Legacy local automation scripts are not part of the active app.

## Typical Local Run

```bash
uv run python scripts/init_database.py
uv run python scripts/start_all.py
```
