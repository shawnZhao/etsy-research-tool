# Etsy Research Tool

A market research tool for Etsy sellers — keyword research, competitor analysis, and listing SEO audit. Built for internal use, targeting SaaS launch later.

## Quick Start

```bash
# Set your Etsy API credentials
cp .env.example .env
# Edit .env with your ETSY_API_KEY, ETSY_API_SECRET, ETSY_REFRESH_TOKEN

# Start all services
docker-compose up -d

# Run database migrations
cd backend && alembic upgrade head

# Open the app
open http://localhost:3000
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12 + FastAPI |
| Frontend | TypeScript + Next.js 16 (App Router) + Tailwind CSS 4 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 (async) |
| Task Queue | Celery + Redis |
| Auth | Etsy OAuth 2.0 PKCE (Redis-backed token management) |
| Deployment | Docker Compose |

## Features

### Keyword Research
- Search Etsy listings by keyword and analyze results
- Search volume estimation, competition scoring (0-100), price analysis
- Related tag extraction and trend direction tracking (rising/falling/stable)
- Trend history with time-series data points

### Competitor Analysis
- Track Etsy shops by URL — fetches shop profile, all listings (up to 500), and runs analysis
- Tag strategy: frequency-ranked tags across the shop (top 50)
- Category distribution with percentage breakdowns (top 10)
- Price range analysis (min, max, avg, median)
- Recent listings with quick SEO audit link

### SEO Audit
- Score individual listings on title, tags, and description (each 0-100)
- Weighted overall score: Title 35% + Tags 40% + Description 25%
- Actionable improvement suggestions with severity levels (high/medium/low)
- Benchmarks for comparing against averages

### UI Features
- **Bilingual support (EN/中文)** — switch language via navbar toggle, persisted in localStorage. All UI text translates; data content stays as-is.
- **Field annotations** — hover over "?" icons next to metric labels to see explanations of what each field means and how it's calculated (bilingual).

## Architecture

All Etsy API calls run through Celery async tasks. The frontend receives an immediate `task_id`, polls for completion, then fetches results from PostgreSQL. Analysis results (scores, tags, trends) are computed offline and stored for instant retrieval.

```
User → Next.js Frontend → FastAPI Backend → Celery Worker → Etsy API
                                ↕                    ↓
                           PostgreSQL ←──── precomputed results
```

## Development

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Worker
cd backend && celery -A app.tasks.celery_app worker --loglevel=info
```

## Project Structure

```
backend/app/
├── main.py              # FastAPI entry, lifespan, 22 API routes
├── api/                 # Route handlers (keywords, shops, seo, tasks, auth)
├── models/              # SQLAlchemy ORM (Keyword, Shop, Listing, RankingSnapshot, SEOAudit)
├── services/            # Business logic (KeywordService, ShopService, SEOService)
├── etsy/                # Etsy API client (httpx, retry, OAuth auth)
├── tasks/               # Celery tasks (keyword search, shop sync, SEO audit)
└── db/                  # Database session, base model mixins

frontend/src/
├── app/                 # Next.js App Router pages (/, /keywords, /shops, /seo)
├── lib/                 # API client, types, i18n dictionaries, field annotations
└── components/          # Shared components (Navbar, Tooltip, InfoBadge, LanguageSwitcher)
```

## Key Design Decisions

1. **All Etsy API calls are async Celery tasks** — frontend polls for completion; no blocking requests
2. **Precomputed analysis in PostgreSQL** — scores, tags, trends calculated offline and stored
3. **JSONB for Etsy raw data** — every model preserves the original API response for future reprocessing
4. **UUID primary keys** — all tables use UUIDs via shared mixin
5. **Lightweight i18n** — React Context + JSON dictionaries + localStorage, no framework dependency
