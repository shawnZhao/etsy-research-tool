# Etsy Research Tool

A market research tool for Etsy sellers — keyword research, competitor analysis, and listing SEO audit.

## Quick Start

```bash
# Set your Etsy API credentials
cp .env.example .env
# Edit .env with your ETSY_API_KEY and ETSY_API_SECRET

# Start all services
docker-compose up -d

# Run database migrations
cd backend && alembic upgrade head

# Open the app
open http://localhost:3000
```

## Architecture

- **Backend:** FastAPI + Celery + PostgreSQL
- **Frontend:** Next.js 14 + TypeScript + Tailwind
- **Data:** Etsy Open API v3

## Development

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Worker
cd backend && celery -A app.tasks.celery_app worker --loglevel=info
```

## Modules

- **Keyword Research** — Search volume estimation, competition scoring, trend tracking
- **Competitor Analysis** — Shop tracking, tag strategy analysis, price/category distribution
- **SEO Audit** — Title/tag/description scoring with actionable improvement suggestions
