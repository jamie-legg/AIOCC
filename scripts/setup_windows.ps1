Write-Host "AIOCC Upload Studio - Windows Setup" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

uv sync

Push-Location "upload-studio"
npm install
Pop-Location

if (-not (Test-Path ".env")) {
    Copy-Item "env.example" ".env"
    Write-Host "Created .env from env.example. Add your API credentials before publishing." -ForegroundColor Yellow
}

uv run python scripts/init_database.py

Write-Host "Setup complete. Run: uv run python scripts/start_all.py" -ForegroundColor Green
