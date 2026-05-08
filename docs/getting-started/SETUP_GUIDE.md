# Setup Guide

## Requirements

- Python 3.11+
- `uv`
- Node.js 18+
- npm

## Install

```bash
uv sync
cd upload-studio
npm install
```

## Environment

Copy `env.example` to `.env` and set:

- `DATABASE_URL`
- `SECRET_KEY`
- `OPENAI_API_KEY`
- platform OAuth credentials when needed

## Database

```bash
uv run python scripts/init_database.py
```
