.PHONY: help install start api studio init-db lint build clean

help:
	@echo "AIOCC Upload Studio commands:"
	@echo "  install   Install Python and UI dependencies"
	@echo "  start     Start API and upload studio UI"
	@echo "  api       Start backend API only"
	@echo "  studio    Start upload studio UI only"
	@echo "  init-db   Create backend database tables"
	@echo "  lint      Run frontend lint"
	@echo "  build     Build frontend"
	@echo "  clean     Remove local caches"

install:
	uv sync
	cd upload-studio && npm install

start:
	uv run python scripts/start_all.py

api:
	uv run python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000

studio:
	cd upload-studio && npm run dev

init-db:
	uv run python scripts/init_database.py

lint:
	cd upload-studio && npm run lint

build:
	cd upload-studio && npm run build

clean:
	rm -rf .pytest_cache .ruff_cache upload-studio/dist
