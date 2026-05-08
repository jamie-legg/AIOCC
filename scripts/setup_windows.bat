@echo off
echo AIOCC Upload Studio - Windows Setup
echo ===================================

uv sync
if %errorlevel% neq 0 exit /b %errorlevel%

cd upload-studio
npm install
if %errorlevel% neq 0 exit /b %errorlevel%
cd ..

if not exist .env copy env.example .env

uv run python scripts/init_database.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo Setup complete. Run: uv run python scripts/start_all.py
