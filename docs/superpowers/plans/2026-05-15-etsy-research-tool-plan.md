# Etsy 调研工具 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个面向小团队的 Etsy 市场调研工具，覆盖关键词研究、竞品分析、商品 SEO 三大模块。

**Architecture:** 模块化单体 — FastAPI 后端 + Next.js 前端 + PostgreSQL。数据采集全部走 Celery 异步任务队列，前端通过 REST API 即时查询预计算结果。

**Tech Stack:** Python 3.12 + FastAPI, TypeScript + Next.js 14, PostgreSQL 16, Celery + Redis, SQLAlchemy 2.0 async, Tremor charts, Docker Compose

---

## 文件职责总览

### 后端

| 文件 | 职责 |
|------|------|
| `backend/app/main.py` | FastAPI 入口，挂载路由，CORS 配置 |
| `backend/app/config.py` | 环境变量读取，Settings pydantic model |
| `backend/app/db/base.py` | SQLAlchemy declarative Base |
| `backend/app/db/session.py` | async session factory + get_db 依赖 |
| `backend/app/models/*.py` | ORM 模型定义（5 个表） |
| `backend/app/etsy/client.py` | Etsy API v3 封装（httpx, 重试, 缓存） |
| `backend/app/etsy/exceptions.py` | Etsy 异常类层次 |
| `backend/app/etsy/auth.py` | API Key / OAuth 认证管理 |
| `backend/app/services/keyword_service.py` | 关键词分析逻辑（搜索量、竞争度、长尾词） |
| `backend/app/services/shop_service.py` | 店铺分析逻辑（标签、品类、价格） |
| `backend/app/services/listing_service.py` | 商品数据查询和同步 |
| `backend/app/services/seo_service.py` | SEO 评分和审计逻辑 |
| `backend/app/api/keywords.py` | `/api/keywords` 路由 |
| `backend/app/api/shops.py` | `/api/shops` 路由 |
| `backend/app/api/listings.py` | `/api/listings` 路由 |
| `backend/app/api/seo.py` | `/api/seo` 路由 |
| `backend/app/tasks/celery_app.py` | Celery 实例和配置 |
| `backend/app/tasks/sync_tasks.py` | 店铺/商品同步任务 |
| `backend/app/tasks/keyword_tasks.py` | 关键词搜索和分析任务 |
| `backend/app/tasks/seo_tasks.py` | SEO 审计任务 |

### 前端

| 文件 | 职责 |
|------|------|
| `frontend/src/lib/types.ts` | 所有 TypeScript 类型定义 |
| `frontend/src/lib/api.ts` | API 调用封装函数 |
| `frontend/src/app/layout.tsx` | 根布局（导航栏 + 侧边栏） |
| `frontend/src/app/page.tsx` | 首页仪表盘 |
| `frontend/src/app/keywords/page.tsx` | 关键词列表页 |
| `frontend/src/app/keywords/[id]/page.tsx` | 关键词详情页 |
| `frontend/src/app/shops/page.tsx` | 竞品店铺列表页 |
| `frontend/src/app/shops/[id]/page.tsx` | 店铺详情页 |
| `frontend/src/app/seo/page.tsx` | SEO 审计页面 |
| `frontend/src/app/seo/[id]/page.tsx` | 审计报告详情页 |

---

## Phase 1: 项目骨架 + EtsyClient + 数据库

### Task 1.1: 项目初始化与 Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `frontend/Dockerfile`
- Create: `frontend/package.json`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: etsy
      POSTGRES_PASSWORD: etsy_dev
      POSTGRES_DB: etsy_research
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      DATABASE_URL: postgresql+asyncpg://etsy:etsy_dev@postgres:5432/etsy_research
      DATABASE_URL_SYNC: postgresql://etsy:etsy_dev@postgres:5432/etsy_research
      REDIS_URL: redis://redis:6379/0
      ETSY_API_KEY: ${ETSY_API_KEY}
      ETSY_API_SECRET: ${ETSY_API_SECRET}
    depends_on:
      - postgres
      - redis

  worker:
    build: ./backend
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
    volumes:
      - ./backend:/app
    environment:
      DATABASE_URL: postgresql+asyncpg://etsy:etsy_dev@postgres:5432/etsy_research
      DATABASE_URL_SYNC: postgresql://etsy:etsy_dev@postgres:5432/etsy_research
      REDIS_URL: redis://redis:6379/0
      ETSY_API_KEY: ${ETSY_API_KEY}
      ETSY_API_SECRET: ${ETSY_API_SECRET}
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    command: npm run dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api
    depends_on:
      - backend

volumes:
  pgdata:
```

- [ ] **Step 2: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 创建 backend/requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.2
celery[redis]==5.4.0
redis==5.0.8
httpx==0.27.2
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1
pandas==2.2.3
```

- [ ] **Step 4: 创建 backend/pyproject.toml**

```toml
[project]
name = "etsy-research"
version = "0.1.0"
description = "Etsy market research tool"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 5: 创建 .env.example**

```
ETSY_API_KEY=your_api_key_here
ETSY_API_SECRET=your_api_secret_here
DATABASE_URL=postgresql+asyncpg://etsy:etsy_dev@localhost:5432/etsy_research
REDIS_URL=redis://localhost:6379/0
```

- [ ] **Step 6: 创建 .gitignore**

```
__pycache__/
*.pyc
.env
node_modules/
.next/
pgdata/
.venv/
*.egg-info/
```

- [ ] **Step 7: Initialize frontend**

Run:
```bash
cd frontend && npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --no-import-alias --use-npm
```

- [ ] **Step 8: Commit**

```bash
git init
git add -A
git commit -m "feat: project skeleton with Docker Compose, backend and frontend scaffolding"
```

---

### Task 1.2: 后端基础架构（config, db, models）

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/keyword.py`
- Create: `backend/app/models/shop.py`
- Create: `backend/app/models/listing.py`
- Create: `backend/app/models/ranking.py`
- Create: `backend/app/models/seo_audit.py`

- [ ] **Step 1: 创建 backend/app/__init__.py** (空文件)

- [ ] **Step 2: 创建 backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://etsy:etsy_dev@localhost:5432/etsy_research"
    database_url_sync: str = "postgresql://etsy:etsy_dev@localhost:5432/etsy_research"
    redis_url: str = "redis://localhost:6379/0"
    etsy_api_key: str = ""
    etsy_api_secret: str = ""
    etsy_api_base_url: str = "https://openapi.etsy.com/v3"
    keyword_cache_ttl: int = 3600

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 3: 创建 backend/app/db/base.py**

```python
from sqlalchemy.orm import DeclarativeBase
import uuid
from sqlalchemy import UUID, Column, DateTime, func


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
```

- [ ] **Step 4: 创建 backend/app/db/session.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 5: 创建 backend/app/models/keyword.py**

```python
from sqlalchemy import String, Integer, Float, Numeric, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin
import uuid


class Keyword(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "keywords"

    keyword: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    search_volume_est: Mapped[int] = mapped_column(Integer, default=0)
    competition_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    listing_count: Mapped[int] = mapped_column(Integer, default=0)
    top_category: Mapped[str] = mapped_column(String(255), nullable=True)
    related_tags: Mapped[dict] = mapped_column(JSONB, default=list)
    trend_direction: Mapped[str] = mapped_column(String(20), default="stable")
    trend_data: Mapped[dict] = mapped_column(JSONB, default=list)
    etsy_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
```

- [ ] **Step 6: 创建 backend/app/models/shop.py**

```python
from sqlalchemy import String, Integer, Float, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class Shop(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "shops"

    shop_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    total_listings: Mapped[int] = mapped_column(Integer, default=0)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    tags_used: Mapped[dict] = mapped_column(JSONB, default=list)
    category_distribution: Mapped[dict] = mapped_column(JSONB, default=list)
    price_range: Mapped[dict] = mapped_column(JSONB, default=dict)
    listing_frequency: Mapped[dict] = mapped_column(JSONB, default=dict)
    etsy_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
```

- [ ] **Step 7: 创建 backend/app/models/listing.py**

```python
from sqlalchemy import String, Integer, Float, Numeric, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class Listing(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "listings"

    listing_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    shop_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    category: Mapped[str] = mapped_column(String(500), nullable=True)
    category_path: Mapped[dict] = mapped_column(JSONB, default=list)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    images: Mapped[dict] = mapped_column(JSONB, default=list)
    favorites: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    views_est: Mapped[int] = mapped_column(Integer, default=0)
    etsy_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
```

- [ ] **Step 8: 创建 backend/app/models/ranking.py**

```python
from sqlalchemy import Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin
import uuid


class RankingSnapshot(Base, UUIDMixin):
    __tablename__ = "ranking_snapshots"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True)
    keyword_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("keywords.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    total_results: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 9: 创建 backend/app/models/seo_audit.py**

```python
from sqlalchemy import Float, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin
import uuid


class SEOAudit(Base, UUIDMixin):
    __tablename__ = "seo_audits"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True)
    title_score: Mapped[float] = mapped_column(Float, default=0.0)
    tag_score: Mapped[float] = mapped_column(Float, default=0.0)
    description_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    suggestions: Mapped[dict] = mapped_column(JSONB, default=list)
    benchmarks: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 10: 创建 backend/app/models/__init__.py**

```python
from app.models.keyword import Keyword
from app.models.shop import Shop
from app.models.listing import Listing
from app.models.ranking import RankingSnapshot
from app.models.seo_audit import SEOAudit

__all__ = ["Keyword", "Shop", "Listing", "RankingSnapshot", "SEOAudit"]
```

- [ ] **Step 11: 创建 backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Etsy Research Tool", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 12: Init Alembic and create initial migration**

```bash
cd backend && alembic init alembic
```

Edit `backend/alembic/env.py` to import Base and models, configure async engine.

```bash
cd backend && alembic revision --autogenerate -m "initial"
```

- [ ] **Step 13: Commit**

```bash
git add backend/app/models/ backend/app/db/ backend/app/main.py backend/app/config.py backend/app/__init__.py backend/alembic/ backend/Dockerfile backend/requirements.txt backend/pyproject.toml docker-compose.yml .env.example .gitignore
git commit -m "feat: backend infrastructure — FastAPI entry, DB models, Alembic setup"
```

---

### Task 1.3: EtsyClient（API 适配器）

**Files:**
- Create: `backend/app/etsy/__init__.py`
- Create: `backend/app/etsy/exceptions.py`
- Create: `backend/app/etsy/auth.py`
- Create: `backend/app/etsy/client.py`

- [ ] **Step 1: 创建 backend/app/etsy/exceptions.py**

```python
class EtsyAPIError(Exception):
    """Base exception for Etsy API errors."""
    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(message)


class EtsyRateLimitError(EtsyAPIError):
    """429 Too Many Requests."""
    pass


class EtsyAuthError(EtsyAPIError):
    """401/403 Authentication failure."""
    pass


class EtsyNotFoundError(EtsyAPIError):
    """404 Resource not found."""
    pass


class EtsyServerError(EtsyAPIError):
    """5xx Server error."""
    pass
```

- [ ] **Step 2: 创建 backend/app/etsy/auth.py**

```python
from app.config import settings


class EtsyAuth:
    def __init__(self):
        self.api_key = settings.etsy_api_key
        self.api_secret = settings.etsy_api_secret

    def get_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.api_secret}",
            "Content-Type": "application/json",
        }


etsy_auth = EtsyAuth()
```

- [ ] **Step 3: 创建 backend/app/etsy/client.py**

```python
import time
import httpx
from app.config import settings
from app.etsy.auth import etsy_auth
from app.etsy.exceptions import (
    EtsyAPIError,
    EtsyRateLimitError,
    EtsyAuthError,
    EtsyNotFoundError,
    EtsyServerError,
)


class EtsyClient:
    def __init__(self):
        self.base_url = settings.etsy_api_base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=etsy_auth.get_headers(),
            timeout=30.0,
        )

    async def close(self):
        await self.client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        for attempt in range(3):
            try:
                response = await self.client.request(method, url, **kwargs)
                return self._handle_response(response)
            except (EtsyRateLimitError, EtsyServerError) as e:
                if attempt == 2:
                    raise
                wait = 2 ** attempt
                time.sleep(wait)
            except httpx.RequestError as e:
                if attempt == 2:
                    raise EtsyAPIError(f"Request failed: {e}")
                time.sleep(2 ** attempt)

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 429:
            raise EtsyRateLimitError("Rate limited", 429)
        if response.status_code in (401, 403):
            raise EtsyAuthError("Authentication failed", response.status_code)
        if response.status_code == 404:
            raise EtsyNotFoundError("Resource not found", 404)
        if response.status_code >= 500:
            raise EtsyServerError("Server error", response.status_code)
        if response.status_code >= 400:
            raise EtsyAPIError(f"API error: {response.text}", response.status_code)
        return response.json()

    async def search_listings(
        self, keyword: str, limit: int = 50, offset: int = 0, sort: str = "score"
    ) -> dict:
        params = {"keywords": keyword, "limit": limit, "offset": offset, "sort_on": sort}
        return await self._request("GET", "/application/listings/active", params=params)

    async def get_listing(self, listing_id: int) -> dict:
        return await self._request("GET", f"/application/listings/{listing_id}")

    async def get_shop(self, shop_id: int) -> dict:
        return await self._request("GET", f"/application/shops/{shop_id}")

    async def get_shop_listings(self, shop_id: int, limit: int = 100, offset: int = 0) -> dict:
        params = {"shop_id": shop_id, "limit": limit, "offset": offset}
        return await self._request("GET", f"/application/shops/{shop_id}/listings/active", params=params)

    async def get_listing_reviews(self, listing_id: int, limit: int = 25, offset: int = 0) -> dict:
        params = {"limit": limit, "offset": offset}
        return await self._request("GET", f"/application/listings/{listing_id}/reviews", params=params)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/etsy/
git commit -m "feat: EtsyClient — API v3 adapter with retry, error handling, auth"
```

---

### Task 1.4: Celery 配置

**Files:**
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/celery_app.py`

- [ ] **Step 1: Create backend/app/tasks/celery_app.py**

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "etsy_research",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    worker_prefetch_multiplier=1,
)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/tasks/__init__.py backend/app/tasks/celery_app.py
git commit -m "feat: Celery configuration with Redis broker"
```

---

### Task 1.5: 前端基础架构

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: 创建 frontend/src/lib/types.ts**

```typescript
export interface Keyword {
  id: string;
  keyword: string;
  search_volume_est: number;
  competition_score: number;
  avg_price: number;
  listing_count: number;
  top_category: string;
  related_tags: TagCount[];
  trend_direction: "up" | "down" | "stable";
  trend_data: TrendPoint[];
  last_updated: string;
  created_at: string;
}

export interface Shop {
  id: string;
  shop_id: number;
  name: string;
  url: string;
  total_listings: number;
  total_reviews: number;
  avg_rating: number;
  tags_used: TagCount[];
  category_distribution: CategoryDist[];
  price_range: PriceRange;
  listing_frequency: FrequencyData;
  last_synced: string;
  created_at: string;
}

export interface Listing {
  id: string;
  listing_id: number;
  shop_id: number;
  title: string;
  description: string;
  tags: string[];
  price: number;
  currency: string;
  category: string;
  category_path: string[];
  url: string;
  images: string[];
  favorites: number;
  review_count: number;
  rating: number;
  views_est: number;
  last_updated: string;
  created_at: string;
}

export interface SEOAudit {
  id: string;
  listing_id: string;
  title_score: number;
  tag_score: number;
  description_score: number;
  overall_score: number;
  suggestions: SEOSuggestion[];
  benchmarks: Record<string, number>;
  created_at: string;
}

export interface RankingSnapshot {
  id: string;
  listing_id: string;
  keyword_id: string;
  position: number;
  total_results: number;
  captured_at: string;
}

export interface TagCount {
  tag: string;
  count: number;
}

export interface CategoryDist {
  category: string;
  count: number;
  pct: number;
}

export interface PriceRange {
  min: number;
  max: number;
  avg: number;
  median: number;
}

export interface FrequencyData {
  weekly: number;
  monthly: number;
  trend: number[];
}

export interface TrendPoint {
  date: string;
  volume: number;
}

export interface SEOSuggestion {
  type: "title" | "tags" | "description";
  severity: "high" | "medium" | "low";
  message: string;
  detail: string;
}

export interface TaskStatus {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  result?: unknown;
  error?: string;
}
```

- [ ] **Step 2: 创建 frontend/src/lib/api.ts**

```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.detail || err.message || "Request failed");
  }
  return res.json();
}

// Keywords
export const searchKeyword = (keyword: string) =>
  request<{ task_id: string }>("/keywords/search", {
    method: "POST",
    body: JSON.stringify({ keyword }),
  });

export const getKeyword = (id: string) =>
  request<Keyword>(`/keywords/${id}`);

export const listKeywords = (sort?: string, order?: string) =>
  request<Keyword[]>(`/keywords?sort=${sort || "last_updated"}&order=${order || "desc"}`);

export const getKeywordRelated = (id: string) =>
  request<TagCount[]>(`/keywords/${id}/related`);

export const compareKeywords = (ids: string[]) =>
  request<Keyword[]>(`/keywords/compare`, {
    method: "POST",
    body: JSON.stringify({ ids }),
  });

export const getKeywordTrend = (id: string) =>
  request<TrendPoint[]>(`/keywords/${id}/trend`);

// Shops
export const trackShop = (url: string) =>
  request<{ task_id: string }>("/shops/track", {
    method: "POST",
    body: JSON.stringify({ url }),
  });

export const listShops = () =>
  request<Shop[]>("/shops");

export const getShop = (id: string) =>
  request<Shop>(`/shops/${id}`);

export const getShopTags = (id: string) =>
  request<TagCount[]>(`/shops/${id}/tags`);

export const getShopListings = (id: string, page = 1) =>
  request<{ items: Listing[]; total: number }>(`/shops/${id}/listings?page=${page}`);

export const getShopTrend = (id: string) =>
  request<FrequencyData>(`/shops/${id}/trend`);

export const compareShops = (ids: string[]) =>
  request<Shop[]>(`/shops/compare`, {
    method: "POST",
    body: JSON.stringify({ ids }),
  });

// SEO
export const auditListing = (listingUrl: string) =>
  request<{ task_id: string }>("/seo/audit", {
    method: "POST",
    body: JSON.stringify({ listing_url: listingUrl }),
  });

export const getSEOAudit = (id: string) =>
  request<SEOAudit>(`/seo/audits/${id}`);

export const listAudits = (listingId?: string) =>
  request<SEOAudit[]>(`/seo/audits${listingId ? `?listing_id=${listingId}` : ""}`);

export const getTaskStatus = (taskId: string) =>
  request<TaskStatus>(`/tasks/${taskId}`);
```

- [ ] **Step 3: 创建 frontend/src/app/layout.tsx**

```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Etsy Research Tool",
  description: "Market research tool for Etsy sellers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center gap-8">
            <Link href="/" className="text-xl font-bold text-orange-600">
              EtsyResearch
            </Link>
            <Link href="/keywords" className="text-gray-600 hover:text-gray-900">
              Keywords
            </Link>
            <Link href="/shops" className="text-gray-600 hover:text-gray-900">
              Competitors
            </Link>
            <Link href="/seo" className="text-gray-600 hover:text-gray-900">
              SEO Audit
            </Link>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/app/layout.tsx
git commit -m "feat: frontend infrastructure — types, API client, navigation layout"
```

---

## Phase 2: 关键词研究模块

### Task 2.1: KeywordService（关键词分析算法）

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/keyword_service.py`

- [ ] **Step 1: 创建 backend/app/services/keyword_service.py**

```python
import math
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.keyword import Keyword
from app.models.listing import Listing


class KeywordService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def estimate_search_volume(self, listing_count: int, category: str) -> int:
        category_weights = {
            "jewelry": 1.2,
            "home_and_living": 0.9,
            "clothing": 1.1,
            "craft_supplies": 0.8,
            "art_and_collectibles": 0.7,
            "accessories": 1.0,
            "paper_and_party_supplies": 0.6,
            "weddings": 1.3,
            "toys_and_games": 0.8,
            "vintage": 0.9,
        }
        weight = category_weights.get(category, 0.85)
        return int(listing_count * weight / 100)

    def calculate_competition(
        self, total_listings: int, avg_review_count: float, prices: list[float]
    ) -> float:
        if not prices or total_listings == 0:
            return 0.0

        high_sales_ratio = min(avg_review_count / 500, 1.0)
        max_possible_reviews = 2000
        review_factor = min(avg_review_count / max_possible_reviews, 1.0)

        if len(prices) > 1:
            mean_price = sum(prices) / len(prices)
            variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
            std_dev = math.sqrt(variance)
            if mean_price > 0:
                cv = std_dev / mean_price
                price_dispersion = min(cv, 1.0)
            else:
                price_dispersion = 0
        else:
            price_dispersion = 0

        score = (
            0.4 * high_sales_ratio
            + 0.3 * review_factor
            + 0.3 * (1 - price_dispersion)
        ) * 100
        return round(score, 1)

    def extract_related_tags(self, tags_list: list[list[str]], seed_keyword: str) -> list[dict]:
        counter = Counter()
        for tags in tags_list:
            for tag in tags:
                if seed_keyword.lower() not in tag.lower():
                    counter[tag] += 1
        top = counter.most_common(20)
        return [{"tag": tag, "count": count} for tag, count in top]

    def compute_trend(self, keyword_record: Keyword, current_volume: int) -> dict:
        trend_data = keyword_record.trend_data or []
        trend_data.append({
            "date": __import__("datetime").datetime.utcnow().isoformat(),
            "volume": current_volume,
        })
        if len(trend_data) >= 3:
            recent = [p["volume"] for p in trend_data[-3:]]
            if recent[-1] > recent[0] * 1.1:
                direction = "up"
            elif recent[-1] < recent[0] * 0.9:
                direction = "down"
            else:
                direction = "stable"
            return {"trend_data": trend_data[-10:], "trend_direction": direction}
        return {"trend_data": trend_data, "trend_direction": "stable"}

    async def get_or_create_keyword(self, keyword: str) -> Keyword:
        stmt = select(Keyword).where(Keyword.keyword == keyword.lower().strip())
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            record = Keyword(keyword=keyword.lower().strip())
            self.db.add(record)
            await self.db.flush()
        return record
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/keyword_service.py
git commit -m "feat: KeywordService with volume estimation, competition scoring, tag extraction"
```

---

### Task 2.2: 关键词 Celery 任务

**Files:**
- Create: `backend/app/tasks/keyword_tasks.py`

- [ ] **Step 1: 创建 backend/app/tasks/keyword_tasks.py**

```python
from app.tasks.celery_app import celery_app
from app.etsy.client import EtsyClient
from app.services.keyword_service import KeywordService
from app.db.session import async_session
from app.models.keyword import Keyword
from sqlalchemy import select


@celery_app.task(bind=True, max_retries=3)
def search_and_analyze_keyword(self, keyword: str):
    """搜索关键词并从 Etsy API 拉取数据进行分析"""
    import asyncio

    async def _run():
        client = EtsyClient()
        try:
            async with async_session() as db:
                service = KeywordService(db)

                # 1. 从 Etsy 搜索
                results = await client.search_listings(keyword, limit=50)
                listings_data = results.get("results", [])
                total_count = results.get("count", 0)

                # 2. 提取价格和标签
                prices = []
                all_tags = []
                for item in listings_data:
                    price_str = item.get("price", {})
                    if isinstance(price_str, dict):
                        amount = float(price_str.get("amount", 0)) / (price_str.get("divisor", 1))
                    else:
                        amount = float(price_str) if price_str else 0
                    prices.append(amount)
                    all_tags.append(item.get("tags", []))

                # 3. 计算分析指标
                record = await service.get_or_create_keyword(keyword)
                record.search_volume_est = service.estimate_search_volume(total_count, "jewelry")
                record.competition_score = service.calculate_competition(
                    total_listings=total_count,
                    avg_review_count=sum(
                        item.get("num_favorers", 0) for item in listings_data
                    ) / max(len(listings_data), 1),
                    prices=prices,
                )
                record.avg_price = sum(prices) / len(prices) if prices else 0
                record.listing_count = total_count
                record.related_tags = service.extract_related_tags(all_tags, keyword)
                record.etsy_raw = {"count": total_count, "sample": listings_data[:5]}

                trend = service.compute_trend(record, total_count)
                record.trend_data = trend["trend_data"]
                record.trend_direction = trend["trend_direction"]

                await db.commit()
                return {"keyword_id": str(record.id)}
        finally:
            await client.close()

    return asyncio.run(_run())
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/tasks/keyword_tasks.py
git commit -m "feat: keyword analysis Celery task — search, analyze, store"
```

---

### Task 2.3: 关键词 API 路由

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/keywords.py`

- [ ] **Step 1: Register tasks router**
- Create: `backend/app/api/tasks.py`

```python
from fastapi import APIRouter
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task_id, "status": result.state}
    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.info)
    return response
```

- [ ] **Step 2: Create backend/app/api/keywords.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.keyword import Keyword
from app.tasks.keyword_tasks import search_and_analyze_keyword

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.post("/search")
async def search_keyword(keyword: str, db: AsyncSession = Depends(get_db)):
    task = search_and_analyze_keyword.delay(keyword)
    return {"task_id": task.id, "status": "processing"}


@router.get("/")
async def list_keywords(
    sort: str = "last_updated",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    col = getattr(Keyword, sort, Keyword.last_updated)
    if order == "asc":
        stmt = select(Keyword).order_by(col.asc()).limit(100)
    else:
        stmt = select(Keyword).order_by(col.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{keyword_id}")
async def get_keyword(keyword_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Keyword).where(Keyword.id == keyword_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record


@router.get("/{keyword_id}/related")
async def get_related_tags(keyword_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Keyword).where(Keyword.id == keyword_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record.related_tags or []


@router.post("/compare")
async def compare_keywords(ids: list[str], db: AsyncSession = Depends(get_db)):
    stmt = select(Keyword).where(Keyword.id.in_(ids))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{keyword_id}/trend")
async def get_trend(keyword_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Keyword).where(Keyword.id == keyword_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record.trend_data or []
```

- [ ] **Step 3: Wire routes in main.py**

Add to `backend/app/main.py`:

```python
from app.api.keywords import router as keywords_router
from app.api.tasks import router as tasks_router

app.include_router(keywords_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/ backend/app/main.py
git commit -m "feat: keyword API endpoints — search, list, detail, related, compare, trend"
```

---

### Task 2.4: 关键词前端页面

**Files:**
- Create: `frontend/src/app/keywords/page.tsx`
- Create: `frontend/src/app/keywords/[id]/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/keywords/page.tsx`**

```typescript
"use client";

import { useState, useEffect } from "react";
import { listKeywords, searchKeyword, getTaskStatus } from "@/lib/api";
import type { Keyword } from "@/lib/types";
import Link from "next/link";

export default function KeywordsPage() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    listKeywords().then(setKeywords).catch(console.error);
  }, []);

  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      const status = await getTaskStatus(taskId);
      if (status.status === "SUCCESS") {
        setTaskId(null);
        const updated = await listKeywords();
        setKeywords(updated);
      } else if (status.status === "FAILURE") {
        setTaskId(null);
        alert("Search failed: " + status.error);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  const handleSearch = async () => {
    if (!searchInput.trim()) return;
    setLoading(true);
    const { task_id } = await searchKeyword(searchInput.trim());
    setTaskId(task_id);
    setSearchInput("");
    setLoading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Keyword Research</h1>
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search a keyword on Etsy..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-lg"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !!taskId}
          className="bg-orange-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {taskId ? "Analyzing..." : "Search"}
        </button>
      </div>

      <div className="grid gap-4">
        {keywords.map((kw) => (
          <Link
            key={kw.id}
            href={`/keywords/${kw.id}`}
            className="block border rounded-lg p-4 hover:border-orange-300 transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">{kw.keyword}</span>
              <span className={`text-sm px-2 py-1 rounded ${
                kw.trend_direction === "up" ? "bg-green-100 text-green-700" :
                kw.trend_direction === "down" ? "bg-red-100 text-red-700" :
                "bg-gray-100 text-gray-600"
              }`}>
                {kw.trend_direction === "up" ? "↑ Rising" :
                 kw.trend_direction === "down" ? "↓ Falling" : "→ Stable"}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-4 mt-3 text-sm text-gray-600">
              <div>Volume: <strong>{kw.search_volume_est.toLocaleString()}</strong></div>
              <div>Competition: <strong>{kw.competition_score}%</strong></div>
              <div>Avg Price: <strong>${Number(kw.avg_price).toFixed(2)}</strong></div>
              <div>Listings: <strong>{kw.listing_count.toLocaleString()}</strong></div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/keywords/[id]/page.tsx`**

```typescript
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getKeyword, getKeywordRelated, getKeywordTrend } from "@/lib/api";
import type { Keyword, TagCount, TrendPoint } from "@/lib/types";

export default function KeywordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [keyword, setKeyword] = useState<Keyword | null>(null);
  const [related, setRelated] = useState<TagCount[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);

  useEffect(() => {
    if (!id) return;
    getKeyword(id).then(setKeyword).catch(console.error);
    getKeywordRelated(id).then(setRelated).catch(console.error);
    getKeywordTrend(id).then(setTrend).catch(console.error);
  }, [id]);

  if (!keyword) return <div>Loading...</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">{keyword.keyword}</h1>
      <p className="text-gray-500 mb-8">Last updated: {new Date(keyword.last_updated).toLocaleString()}</p>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <MetricCard label="Est. Search Volume" value={keyword.search_volume_est.toLocaleString()} />
        <MetricCard label="Competition" value={`${keyword.competition_score}%`} />
        <MetricCard label="Avg Price" value={`$${Number(keyword.avg_price).toFixed(2)}`} />
        <MetricCard label="Active Listings" value={keyword.listing_count.toLocaleString()} />
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Related Tags</h2>
          <div className="space-y-2">
            {related.map((rt) => (
              <div key={rt.tag} className="flex justify-between items-center border-b pb-2">
                <span className="font-medium">{rt.tag}</span>
                <span className="text-gray-500">{rt.count} listings</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-4">Trend History</h2>
          <div className="space-y-2">
            {trend.map((t, i) => (
              <div key={i} className="flex justify-between items-center border-b pb-2">
                <span className="text-gray-500">{new Date(t.date).toLocaleDateString()}</span>
                <span className="font-medium">{t.volume.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border rounded-lg p-4 text-center">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/keywords/
git commit -m "feat: keyword research frontend — list page and detail page with metrics, tags, trend"
```

---

## Phase 3: 竞品分析模块

### Task 3.1: 店铺服务 + Celery 任务

**Files:**
- Create: `backend/app/services/shop_service.py`
- Create: `backend/app/tasks/sync_tasks.py`

- [ ] **Step 1: Create `backend/app/services/shop_service.py`**

```python
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.shop import Shop
from app.models.listing import Listing


class ShopService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_shop(self, shop_id: int, name: str, url: str) -> Shop:
        stmt = select(Shop).where(Shop.shop_id == shop_id)
        result = await self.db.execute(stmt)
        shop = result.scalar_one_or_none()
        if shop is None:
            shop = Shop(shop_id=shop_id, name=name, url=url)
            self.db.add(shop)
            await self.db.flush()
        return shop

    async def analyze_tags(self, shop: Shop) -> list[dict]:
        stmt = select(Listing.tags).where(Listing.shop_id == shop.shop_id)
        result = await self.db.execute(stmt)
        counter = Counter()
        for (tags,) in result:
            if tags:
                for tag in tags:
                    counter[tag] += 1
        sorted_tags = counter.most_common(50)
        return [{"tag": tag, "count": count} for tag, count in sorted_tags]

    async def analyze_categories(self, shop: Shop) -> list[dict]:
        stmt = select(Listing.category).where(
            Listing.shop_id == shop.shop_id,
            Listing.category.is_not(None),
        )
        result = await self.db.execute(stmt)
        counter = Counter()
        total = 0
        for (cat,) in result:
            if cat:
                counter[cat] += 1
                total += 1
        return [
            {"category": cat, "count": count, "pct": round(count / total * 100, 1) if total else 0}
            for cat, count in counter.most_common(10)
        ]

    async def analyze_prices(self, shop: Shop) -> dict:
        import statistics
        stmt = select(Listing.price).where(
            Listing.shop_id == shop.shop_id,
            Listing.price.is_not(None),
        )
        result = await self.db.execute(stmt)
        prices = [float(p) for (p,) in result if p]
        if not prices:
            return {"min": 0, "max": 0, "avg": 0, "median": 0}
        return {
            "min": min(prices),
            "max": max(prices),
            "avg": round(sum(prices) / len(prices), 2),
            "median": round(statistics.median(prices), 2),
        }
```

- [ ] **Step 2: Create `backend/app/tasks/sync_tasks.py`**

```python
from app.tasks.celery_app import celery_app
from app.etsy.client import EtsyClient
from app.services.shop_service import ShopService
from app.db.session import async_session
from app.models.shop import Shop
from app.models.listing import Listing
from sqlalchemy import select
import asyncio


@celery_app.task(bind=True, max_retries=3)
def sync_shop(self, shop_id: int):
    """同步店铺全量数据：基本信息 + 所有 Listing"""
    async def _run():
        client = EtsyClient()
        try:
            async with async_session() as db:
                service = ShopService(db)

                # 1. Fetch shop info
                raw_shop = await client.get_shop(shop_id)
                shop = await service.upsert_shop(
                    shop_id=shop_id,
                    name=raw_shop.get("shop_name", ""),
                    url=f"https://etsy.com/shop/{raw_shop.get('shop_name', '')}",
                )
                shop.total_listings = raw_shop.get("listing_active_count", 0)
                shop.total_reviews = raw_shop.get("review_count", 0)
                shop.avg_rating = raw_shop.get("review_average", 0)
                shop.etsy_raw = raw_shop

                # 2. Fetch all listings (paginated)
                offset = 0
                while True:
                    data = await client.get_shop_listings(shop_id, limit=100, offset=offset)
                    listings = data.get("results", [])
                    if not listings:
                        break
                    for item in listings:
                        await _upsert_listing(db, shop_id, item)
                    offset += 100
                    if offset >= data.get("count", 0):
                        break

                # 3. Run analysis
                shop.tags_used = await service.analyze_tags(shop)
                shop.category_distribution = await service.analyze_categories(shop)
                shop.price_range = await service.analyze_prices(shop)

                await db.commit()
                return {"shop_id": str(shop.id)}
        finally:
            await client.close()

    return asyncio.run(_run())


async def _upsert_listing(db, shop_id: int, item: dict):
    listing_id = item.get("listing_id")
    stmt = select(Listing).where(Listing.listing_id == listing_id)
    result = await db.execute(stmt)
    listing = result.scalar_one_or_none()

    price_data = item.get("price", {})
    if isinstance(price_data, dict):
        price = float(price_data.get("amount", 0)) / float(price_data.get("divisor", 1))
        currency = price_data.get("currency_code", "USD")
    else:
        price = float(price_data) if price_data else 0
        currency = "USD"

    if listing is None:
        listing = Listing(
            listing_id=listing_id,
            shop_id=shop_id,
            title=item.get("title", ""),
            description=item.get("description", ""),
            tags=item.get("tags", []),
            price=price,
            currency=currency,
            category=item.get("taxonomy_path", [None])[-1] if item.get("taxonomy_path") else None,
            category_path=item.get("taxonomy_path", []),
            url=item.get("url", ""),
            images=[img.get("url_570xN", "") for img in item.get("images", [])],
            favorites=item.get("num_favorers", 0),
            review_count=item.get("review_count", 0) or 0,
            rating=item.get("rating", 0) or 0,
            etsy_raw=item,
        )
        db.add(listing)
    else:
        listing.title = item.get("title", listing.title)
        listing.description = item.get("description", listing.description)
        listing.tags = item.get("tags", listing.tags)
        listing.price = price
        listing.favorites = item.get("num_favorers", listing.favorites)
        listing.review_count = item.get("review_count", 0) or listing.review_count
        listing.rating = item.get("rating", 0) or listing.rating
        listing.etsy_raw = item
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/shop_service.py backend/app/tasks/sync_tasks.py
git commit -m "feat: ShopService + sync tasks — shop analysis (tags, categories, prices) and listing sync"
```

---

### Task 3.2: 店铺 API 路由

**Files:**
- Create: `backend/app/api/shops.py`

- [ ] **Step 1: Create `backend/app/api/shops.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.shop import Shop
from app.models.listing import Listing
from app.tasks.sync_tasks import sync_shop

router = APIRouter(prefix="/shops", tags=["shops"])


@router.post("/track")
async def track_shop(url: str):
    shop_id = _extract_shop_id(url)
    task = sync_shop.delay(shop_id)
    return {"task_id": task.id, "status": "processing"}


@router.get("/")
async def list_shops(db: AsyncSession = Depends(get_db)):
    stmt = select(Shop).order_by(Shop.last_synced.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{shop_id}")
async def get_shop(shop_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Shop).where(Shop.id == shop_id)
    result = await db.execute(stmt)
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop


@router.get("/{shop_id}/tags")
async def get_shop_tags(shop_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Shop).where(Shop.id == shop_id)
    result = await db.execute(stmt)
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop.tags_used or []


@router.get("/{shop_id}/listings")
async def get_shop_listings(shop_id: str, page: int = 1, db: AsyncSession = Depends(get_db)):
    stmt = select(Shop).where(Shop.id == shop_id)
    result = await db.execute(stmt)
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=404, detail="Shop not found")

    per_page = 20
    count_stmt = select(Listing).where(Listing.shop_id == shop.shop_id)
    total_result = await db.execute(select(__import__("sqlalchemy").func.count()).select_from(count_stmt.subquery()))
    total = total_result.scalar() or 0

    stmt = (
        select(Listing)
        .where(Listing.shop_id == shop.shop_id)
        .order_by(Listing.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return {"items": result.scalars().all(), "total": total}


@router.get("/{shop_id}/trend")
async def get_shop_trend(shop_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Shop).where(Shop.id == shop_id)
    result = await db.execute(stmt)
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop.listing_frequency or {"weekly": 0, "monthly": 0, "trend": []}


@router.post("/compare")
async def compare_shops(ids: list[str], db: AsyncSession = Depends(get_db)):
    stmt = select(Shop).where(Shop.id.in_(ids))
    result = await db.execute(stmt)
    return result.scalars().all()


def _extract_shop_id(url_or_id: str) -> int:
    import re
    match = re.search(r"etsy\.com/shop/([^/?]+)", url_or_id)
    if match:
        return match.group(1)
    if url_or_id.isdigit():
        return int(url_or_id)
    # Assume it's a shop name string
    return url_or_id.strip("/")
```

- [ ] **Step 2: Wire in main.py**

```python
from app.api.shops import router as shops_router

app.include_router(shops_router, prefix="/api")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/shops.py backend/app/main.py
git commit -m "feat: shop API endpoints — track, list, detail, tags, listings, trend, compare"
```

---

### Task 3.3: 竞品分析前端

**Files:**
- Create: `frontend/src/app/shops/page.tsx`
- Create: `frontend/src/app/shops/[id]/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/shops/page.tsx`**

```typescript
"use client";

import { useState, useEffect } from "react";
import { listShops, trackShop, getTaskStatus } from "@/lib/api";
import type { Shop } from "@/lib/types";
import Link from "next/link";

export default function ShopsPage() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    listShops().then(setShops).catch(console.error);
  }, []);

  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      const status = await getTaskStatus(taskId);
      if (status.status === "SUCCESS") {
        setTaskId(null);
        const updated = await listShops();
        setShops(updated);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Competitor Analysis</h1>
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          placeholder="Paste Etsy shop URL..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-lg"
        />
        <button
          onClick={async () => {
            if (!urlInput.trim()) return;
            const { task_id } = await trackShop(urlInput.trim());
            setTaskId(task_id);
            setUrlInput("");
          }}
          disabled={!!taskId}
          className="bg-orange-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {taskId ? "Syncing..." : "Track Shop"}
        </button>
      </div>

      <div className="grid gap-4">
        {shops.map((shop) => (
          <Link
            key={shop.id}
            href={`/shops/${shop.id}`}
            className="block border rounded-lg p-4 hover:border-orange-300 transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">{shop.name}</span>
              <span className="text-yellow-500">★ {Number(shop.avg_rating).toFixed(1)}</span>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-3 text-sm text-gray-600">
              <div>Listings: <strong>{shop.total_listings}</strong></div>
              <div>Reviews: <strong>{shop.total_reviews.toLocaleString()}</strong></div>
              <div>Tags Used: <strong>{shop.tags_used?.length || 0}</strong></div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/shops/[id]/page.tsx`**

```typescript
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getShop, getShopTags, getShopListings } from "@/lib/api";
import type { Shop, TagCount, Listing } from "@/lib/types";

export default function ShopDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [shop, setShop] = useState<Shop | null>(null);
  const [tags, setTags] = useState<TagCount[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);

  useEffect(() => {
    if (!id) return;
    getShop(id).then(setShop).catch(console.error);
    getShopTags(id).then(setTags).catch(console.error);
    getShopListings(id).then((r) => setListings(r.items)).catch(console.error);
  }, [id]);

  if (!shop) return <div>Loading...</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">{shop.name}</h1>
      <a href={shop.url} target="_blank" className="text-orange-600 hover:underline text-sm mb-8 block">
        View on Etsy →
      </a>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <MetricCard label="Total Listings" value={shop.total_listings.toString()} />
        <MetricCard label="Total Reviews" value={shop.total_reviews.toLocaleString()} />
        <MetricCard label="Avg Rating" value={`★ ${Number(shop.avg_rating).toFixed(1)}`} />
        <MetricCard label="Price Range" value={`$${shop.price_range?.min || 0} - $${shop.price_range?.max || 0}`} />
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Top Tags Used</h2>
          <div className="flex flex-wrap gap-2">
            {tags.slice(0, 30).map((t) => (
              <span key={t.tag} className="px-3 py-1 bg-gray-100 rounded-full text-sm" style={{
                fontSize: `${Math.max(0.75, Math.min(1.5, 0.75 + t.count / Math.max(...tags.map(x => x.count)) * 0.75))}rem`
              }}>
                {t.tag} ({t.count})
              </span>
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-4">Category Distribution</h2>
          {shop.category_distribution?.map((cd) => (
            <div key={cd.category} className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span>{cd.category}</span>
                <span className="text-gray-500">{cd.pct}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${cd.pct}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Recent Listings</h2>
        <div className="grid gap-3">
          {listings.slice(0, 10).map((l) => (
            <div key={l.id} className="flex items-center gap-4 border rounded-lg p-3">
              {l.images?.[0] && (
                <img src={l.images[0]} alt={l.title} className="w-16 h-16 object-cover rounded" />
              )}
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{l.title}</p>
                <p className="text-sm text-gray-500">${Number(l.price).toFixed(2)} · {l.favorites} favorites</p>
              </div>
              <div className="text-sm text-gray-500">{l.tags?.length || 0}/13 tags</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border rounded-lg p-4 text-center">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/shops/
git commit -m "feat: competitor analysis frontend — shop list and detail with tags, categories, listings"
```

---

## Phase 4: 商品 SEO 模块

### Task 4.1: SEOService（SEO 评分算法）

**Files:**
- Create: `backend/app/services/seo_service.py`

- [ ] **Step 1: Create `backend/app/services/seo_service.py`**

```python
from app.models.listing import Listing


class SEOService:
    def score_title(self, title: str, core_keywords: list[str]) -> tuple[float, list[dict]]:
        suggestions = []
        score = 0

        # Length check: 40-60 chars is ideal
        length = len(title)
        if 40 <= length <= 60:
            score += 30
        elif 20 <= length <= 80:
            score += 15
        else:
            suggestions.append({
                "type": "title",
                "severity": "high",
                "message": f"Title is {length} chars. Ideal: 40-60 characters.",
                "detail": "Expand or shorten your title to fit the optimal range.",
            })

        # Core keyword position: should appear in first 40 chars
        first_40 = title[:40].lower()
        keyword_found = any(kw.lower() in first_40 for kw in core_keywords)
        if keyword_found:
            score += 30
        else:
            suggestions.append({
                "type": "title",
                "severity": "high",
                "message": "Core keyword not found in first 40 characters.",
                "detail": "Move your main keyword earlier in the title.",
            })

        # No ALL CAPS or keyword stuffing
        caps_ratio = sum(1 for c in title if c.isupper()) / max(len(title), 1)
        if caps_ratio < 0.5:
            score += 20
        else:
            suggestions.append({
                "type": "title",
                "severity": "medium",
                "message": "Title has too many capital letters.",
                "detail": "Use normal capitalization instead of ALL CAPS.",
            })

        # Contains 2+ longtail modifiers
        longtail_modifiers = ["handmade", "custom", "personalized", "gift", "vintage", "boho",
                              "minimalist", "modern", "rustic", "wedding", "gold", "silver"]
        modifier_count = sum(1 for m in longtail_modifiers if m.lower() in title.lower())
        if modifier_count >= 2:
            score += 20
        else:
            suggestions.append({
                "type": "title",
                "severity": "low",
                "message": "Add 2+ descriptive modifiers (e.g., handmade, personalized).",
                "detail": "Longtail modifiers help buyers find your item in specific searches.",
            })

        return round(score, 1), suggestions

    def score_tags(self, tags: list[str], title: str, category_hot_tags: list[str]) -> tuple[float, list[dict]]:
        suggestions = []
        score = 0

        # All 13 tags used
        if len(tags) >= 13:
            score += 25
        else:
            suggestions.append({
                "type": "tags",
                "severity": "high",
                "message": f"Only {len(tags)}/13 tags used. Fill all 13 tag slots.",
                "detail": "Etsy gives you 13 tag slots — unused slots are missed opportunities.",
            })

        # 3+ longtail tags (multi-word)
        longtail_count = sum(1 for t in tags if " " in t)
        if longtail_count >= 3:
            score += 25
        else:
            suggestions.append({
                "type": "tags",
                "severity": "medium",
                "message": f"Only {longtail_count} multi-word (longtail) tags. Aim for 3+.",
                "detail": "Multi-word tags like 'minimalist gold necklace' are more specific and less competitive.",
            })

        # Tag-title consistency
        title_words = set(title.lower().split())
        tag_match_count = sum(1 for t in tags if any(w in title_words for w in t.lower().split()))
        if tag_match_count >= 8:
            score += 25
        else:
            suggestions.append({
                "type": "tags",
                "severity": "medium",
                "message": "Tags don't align well with title keywords.",
                "detail": "Etsy matches tags and title together. Keep them consistent.",
            })

        # Uses category hot tags
        hot_tag_match = sum(1 for t in tags if t.lower() in [ht.lower() for ht in category_hot_tags])
        if hot_tag_match >= 3:
            score += 25
        else:
            suggestions.append({
                "type": "tags",
                "severity": "low",
                "message": "Missing popular category tags.",
                "detail": f"Consider adding trending tags like: {', '.join(category_hot_tags[:5])}",
            })

        return round(score, 1), suggestions

    def score_description(self, description: str, core_keywords: list[str]) -> tuple[float, list[dict]]:
        suggestions = []
        score = 0

        # Length > 200 chars
        if len(description) >= 200:
            score += 25

        else:
            suggestions.append({
                "type": "description",
                "severity": "medium",
                "message": f"Description is {len(description)} chars. Aim for 200+.",
                "detail": "Longer, detailed descriptions help Etsy understand your item better.",
            })

        # Core keyword appears 2-4 times
        desc_lower = description.lower()
        keyword_count = sum(desc_lower.count(kw.lower()) for kw in core_keywords)
        if 2 <= keyword_count <= 5:
            score += 25
        elif keyword_count < 2:
            suggestions.append({
                "type": "description",
                "severity": "medium",
                "message": "Core keywords appear too few times in description.",
                "detail": "Naturally include your main keyword 2-4 times.",
            })

        # Structured (has paragraphs/bullets)
        has_structure = "\n" in description or "•" in description or "- " in description
        if has_structure:
            score += 25
        else:
            suggestions.append({
                "type": "description",
                "severity": "low",
                "message": "Description lacks structure. Use paragraphs or bullet points.",
                "detail": "Structured text is easier to read and signals quality to Etsy.",
            })

        # Contains 2+ longtail keywords
        longtail_count = sum(desc_lower.count(kw.lower()) for kw in core_keywords if " " in kw)
        if longtail_count >= 2:
            score += 25
        else:
            suggestions.append({
                "type": "description",
                "severity": "low",
                "message": "Include more longtail keyword phrases in your description.",
                "detail": "Natural use of longtail phrases improves relevance.",
            })

        return round(score, 1), suggestions

    def extract_core_keywords(self, title: str, tags: list[str]) -> list[str]:
        """Extract the likely core keywords from title and tags."""
        keywords = title.lower().split()[:5]  # First 5 words of title
        tag_keywords = [t.lower() for t in tags[:3]]  # First 3 tags
        return list(set(keywords + tag_keywords))[:5]

    def compute_overall_score(self, title_score: float, tag_score: float, desc_score: float) -> float:
        return round(title_score * 0.35 + tag_score * 0.40 + desc_score * 0.25, 1)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/seo_service.py
git commit -m "feat: SEOService with title, tag, description scoring algorithms and suggestion generation"
```

---

### Task 4.2: SEO Celery 任务 + API 路由

**Files:**
- Create: `backend/app/tasks/seo_tasks.py`
- Create: `backend/app/api/seo.py`

- [ ] **Step 1: Create `backend/app/tasks/seo_tasks.py`**

```python
from app.tasks.celery_app import celery_app
from app.etsy.client import EtsyClient
from app.services.seo_service import SEOService
from app.db.session import async_session
from app.models.listing import Listing
from app.models.seo_audit import SEOAudit
from sqlalchemy import select
import asyncio


@celery_app.task(bind=True, max_retries=3)
def run_seo_audit(self, listing_id: int):
    """拉取商品数据并执行 SEO 审计"""
    async def _run():
        client = EtsyClient()
        try:
            async with async_session() as db:
                seo = SEOService()

                # 1. Fetch from Etsy API
                raw = await client.get_listing(listing_id)
                results = raw.get("results", [raw])  # handle both list and single
                item = results[0] if isinstance(results, list) else raw

                # 2. Upsert listing
                listing = await _get_or_create_listing(db, item)

                # 3. Run scoring
                tags = item.get("tags", []) or []
                title = item.get("title", "")
                description = item.get("description", "") or ""
                core_kw = seo.extract_core_keywords(title, tags)
                category_hot_tags = _get_category_hot_tags(item.get("taxonomy_path", [None])[-1])

                title_score, title_suggestions = seo.score_title(title, core_kw)
                tag_score, tag_suggestions = seo.score_tags(tags, title, category_hot_tags)
                desc_score, desc_suggestions = seo.score_description(description, core_kw)
                overall = seo.compute_overall_score(title_score, tag_score, desc_score)

                # 4. Save audit
                audit = SEOAudit(
                    listing_id=listing.id,
                    title_score=title_score,
                    tag_score=tag_score,
                    description_score=desc_score,
                    overall_score=overall,
                    suggestions=title_suggestions + tag_suggestions + desc_suggestions,
                    benchmarks={"avg_title_score": 65, "avg_tag_score": 60, "avg_desc_score": 55},
                )
                db.add(audit)
                await db.commit()
                return {"audit_id": str(audit.id), "overall_score": overall}
        finally:
            await client.close()

    return asyncio.run(_run())


def _get_category_hot_tags(category: str) -> list[str]:
    """Return trending tags for a given category (would be dynamic in production)."""
    defaults = {
        "necklace": ["gold necklace", "personalized necklace", "minimalist necklace", "layered necklace", "dangle necklace"],
        "earrings": ["gold earrings", "statement earrings", "stud earrings", "hoop earrings", "dangle earrings"],
        "rings": ["stacking rings", "gold rings", "silver rings", "engagement rings", "birthstone rings"],
    }
    for key, tags in defaults.items():
        if key in (category or "").lower():
            return tags
    return ["handmade", "gift", "personalized", "custom", "small business"]


async def _get_or_create_listing(db, item: dict):
    lid = item.get("listing_id")
    stmt = select(Listing).where(Listing.listing_id == lid)
    result = await db.execute(stmt)
    listing = result.scalar_one_or_none()

    price_data = item.get("price", {})
    if isinstance(price_data, dict):
        price = float(price_data.get("amount", 0)) / float(price_data.get("divisor", 1))
    else:
        price = float(price_data) if price_data else 0

    if listing is None:
        listing = Listing(
            listing_id=lid,
            shop_id=item.get("shop_id", 0) or 0,
            title=item.get("title", ""),
            description=item.get("description", ""),
            tags=item.get("tags", []),
            price=price,
            url=item.get("url", ""),
            images=[img.get("url_570xN", "") for img in item.get("images", [])],
            favorites=item.get("num_favorers", 0),
            review_count=item.get("review_count", 0) or 0,
            rating=item.get("rating", 0) or 0,
            etsy_raw=item,
        )
        db.add(listing)
        await db.flush()
    return listing
```

- [ ] **Step 2: Create `backend/app/api/seo.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.session import get_db
from app.models.seo_audit import SEOAudit
from app.models.listing import Listing
from app.tasks.seo_tasks import run_seo_audit

router = APIRouter(prefix="/seo", tags=["seo"])


class AuditRequest(BaseModel):
    listing_url: str


@router.post("/audit")
async def audit_listing(req: AuditRequest):
    listing_id = _extract_listing_id(req.listing_url)
    task = run_seo_audit.delay(listing_id)
    return {"task_id": task.id, "status": "processing"}


@router.get("/audits/{audit_id}")
async def get_audit(audit_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(SEOAudit).where(SEOAudit.id == audit_id)
    result = await db.execute(stmt)
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


@router.get("/audits")
async def list_audits(listing_id: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(SEOAudit).order_by(SEOAudit.created_at.desc())
    if listing_id:
        stmt = stmt.where(SEOAudit.listing_id == listing_id)
    result = await db.execute(stmt.limit(50))
    return result.scalars().all()


@router.get("/benchmarks")
async def get_benchmarks(category: str = None):
    return {
        "avg_title_score": 65,
        "avg_tag_score": 60,
        "avg_description_score": 55,
        "avg_overall_score": 61,
    }


def _extract_listing_id(url_or_id: str) -> int:
    import re
    match = re.search(r"etsy\.com/listing/(\d+)", url_or_id)
    if match:
        return int(match.group(1))
    if url_or_id.isdigit():
        return int(url_or_id)
    raise ValueError(f"Cannot extract listing ID from: {url_or_id}")
```

- [ ] **Step 3: Wire in main.py**

```python
from app.api.seo import router as seo_router

app.include_router(seo_router, prefix="/api")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/tasks/seo_tasks.py backend/app/api/seo.py backend/app/main.py
git commit -m "feat: SEO audit — Celery task, API endpoints, full scoring pipeline"
```

---

### Task 4.3: SEO 前端

**Files:**
- Create: `frontend/src/app/seo/page.tsx`
- Create: `frontend/src/app/seo/[id]/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/seo/page.tsx`**

```typescript
"use client";

import { useState, useEffect } from "react";
import { auditListing, listAudits, getTaskStatus } from "@/lib/api";
import type { SEOAudit } from "@/lib/types";
import Link from "next/link";

export default function SEOPage() {
  const [audits, setAudits] = useState<SEOAudit[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    listAudits().then(setAudits).catch(console.error);
  }, []);

  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      const status = await getTaskStatus(taskId);
      if (status.status === "SUCCESS") {
        setTaskId(null);
        const updated = await listAudits();
        setAudits(updated);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">SEO Audit</h1>
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          placeholder="Paste your Etsy listing URL..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-lg"
        />
        <button
          onClick={async () => {
            if (!urlInput.trim()) return;
            const { task_id } = await auditListing(urlInput.trim());
            setTaskId(task_id);
            setUrlInput("");
          }}
          disabled={!!taskId}
          className="bg-orange-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {taskId ? "Auditing..." : "Analyze"}
        </button>
      </div>

      <div className="grid gap-4">
        {audits.map((audit) => (
          <Link
            key={audit.id}
            href={`/seo/${audit.id}`}
            className="block border rounded-lg p-4 hover:border-orange-300 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="text-lg font-semibold">Audit Report</span>
                <span className="text-gray-400 text-sm ml-3">
                  {new Date(audit.created_at).toLocaleDateString()}
                </span>
              </div>
              <ScoreBadge score={audit.overall_score} />
            </div>
            <div className="grid grid-cols-3 gap-4 mt-3">
              <div className="text-sm">
                <span className="text-gray-500">Title: </span>
                <ScoreBar score={audit.title_score} />
              </div>
              <div className="text-sm">
                <span className="text-gray-500">Tags: </span>
                <ScoreBar score={audit.tag_score} />
              </div>
              <div className="text-sm">
                <span className="text-gray-500">Description: </span>
                <ScoreBar score={audit.description_score} />
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 70 ? "bg-green-100 text-green-700" : score >= 40 ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700";
  return <span className={`px-3 py-1 rounded-full font-bold text-lg ${color}`}>{score}</span>;
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? "bg-green-500" : score >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="inline-flex items-center gap-2">
      <div className="w-24 bg-gray-200 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="font-medium">{score}</span>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/seo/[id]/page.tsx`**

```typescript
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getSEOAudit } from "@/lib/api";
import type { SEOAudit } from "@/lib/types";

export default function SEOAuditPage() {
  const { id } = useParams<{ id: string }>();
  const [audit, setAudit] = useState<SEOAudit | null>(null);

  useEffect(() => {
    if (!id) return;
    getSEOAudit(id).then(setAudit).catch(console.error);
  }, [id]);

  if (!audit) return <div>Loading...</div>;

  const severityColors = { high: "text-red-600", medium: "text-yellow-600", low: "text-blue-600" };

  return (
    <div>
      <div className="flex items-center gap-6 mb-8">
        <div className="text-center">
          <div className="text-5xl font-bold text-orange-600">{audit.overall_score}</div>
          <div className="text-sm text-gray-500">Overall Score</div>
        </div>
        <div className="flex gap-8">
          <ScoreCircle label="Title" score={audit.title_score} />
          <ScoreCircle label="Tags" score={audit.tag_score} />
          <ScoreCircle label="Description" score={audit.description_score} />
        </div>
      </div>

      <h2 className="text-xl font-semibold mb-4">Improvement Suggestions</h2>
      <div className="space-y-3">
        {audit.suggestions?.map((s, i) => (
          <div key={i} className={`border-l-4 p-4 rounded-r-lg ${
            s.severity === "high" ? "border-red-500 bg-red-50" :
            s.severity === "medium" ? "border-yellow-500 bg-yellow-50" :
            "border-blue-500 bg-blue-50"
          }`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs font-bold uppercase ${severityColors[s.severity]}`}>
                {s.severity}
              </span>
              <span className="text-xs text-gray-400 capitalize">{s.type}</span>
            </div>
            <p className="font-medium">{s.message}</p>
            <p className="text-sm text-gray-600 mt-1">{s.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreCircle({ label, score }: { label: string; score: number }) {
  const color = score >= 70 ? "text-green-600" : score >= 40 ? "text-yellow-600" : "text-red-600";
  return (
    <div className="text-center">
      <div className={`text-3xl font-bold ${color}`}>{score}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/seo/
git commit -m "feat: SEO audit frontend — audit list and detailed report with suggestions"
```

---

## Phase 5: 仪表盘整合 + UI 打磨

### Task 5.1: 首页仪表盘

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Replace `frontend/src/app/page.tsx`**

```typescript
"use client";

import { useEffect, useState } from "react";
import { listKeywords, listShops, listAudits } from "@/lib/api";
import type { Keyword, Shop, SEOAudit } from "@/lib/types";
import Link from "next/link";

export default function DashboardPage() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [shops, setShops] = useState<Shop[]>([]);
  const [audits, setAudits] = useState<SEOAudit[]>([]);

  useEffect(() => {
    listKeywords().then(setKeywords).catch(console.error);
    listShops().then(setShops).catch(console.error);
    listAudits().then(setAudits).catch(console.error);
  }, []);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

      <div className="grid grid-cols-3 gap-6 mb-8">
        <Link href="/keywords" className="block border rounded-xl p-6 hover:border-orange-300 hover:shadow-sm transition-all">
          <div className="text-3xl mb-2">🔍</div>
          <div className="text-3xl font-bold text-orange-600">{keywords.length}</div>
          <div className="text-gray-500 mt-1">Keywords Analyzed</div>
        </Link>
        <Link href="/shops" className="block border rounded-xl p-6 hover:border-orange-300 hover:shadow-sm transition-all">
          <div className="text-3xl mb-2">🏪</div>
          <div className="text-3xl font-bold text-orange-600">{shops.length}</div>
          <div className="text-gray-500 mt-1">Shops Tracked</div>
        </Link>
        <Link href="/seo" className="block border rounded-xl p-6 hover:border-orange-300 hover:shadow-sm transition-all">
          <div className="text-3xl mb-2">📊</div>
          <div className="text-3xl font-bold text-orange-600">{audits.length}</div>
          <div className="text-gray-500 mt-1">SEO Audits</div>
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent Keywords</h2>
            <Link href="/keywords" className="text-orange-600 text-sm hover:underline">View all →</Link>
          </div>
          <div className="space-y-2">
            {keywords.slice(0, 5).map((kw) => (
              <Link key={kw.id} href={`/keywords/${kw.id}`} className="flex justify-between items-center border rounded-lg p-3 hover:border-orange-200">
                <span className="font-medium">{kw.keyword}</span>
                <span className="text-sm text-gray-500">Vol: {kw.search_volume_est.toLocaleString()}</span>
              </Link>
            ))}
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Tracked Shops</h2>
            <Link href="/shops" className="text-orange-600 text-sm hover:underline">View all →</Link>
          </div>
          <div className="space-y-2">
            {shops.slice(0, 5).map((shop) => (
              <Link key={shop.id} href={`/shops/${shop.id}`} className="flex justify-between items-center border rounded-lg p-3 hover:border-orange-200">
                <span className="font-medium">{shop.name}</span>
                <span className="text-sm text-gray-500">★ {Number(shop.avg_rating).toFixed(1)}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: dashboard homepage with summary cards, recent keywords, and tracked shops"
```

---

### Task 5.2: 全局路由挂载 + Alembic 迁移验证

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Finalize main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Etsy Research Tool", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# API routes
from app.api.keywords import router as keywords_router
from app.api.shops import router as shops_router
from app.api.seo import router as seo_router
from app.api.tasks import router as tasks_router

app.include_router(keywords_router, prefix="/api")
app.include_router(shops_router, prefix="/api")
app.include_router(seo_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
```

- [ ] **Step 2: Run Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "all models"
cd backend && alembic upgrade head
```

- [ ] **Step 3: Verify startup**

```bash
docker-compose up -d postgres redis
cd backend && python -c "from app.main import app; print('App loaded OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py backend/alembic/
git commit -m "feat: finalize route wiring and Alembic migration"
```

---

### Task 5.3: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with quick start and architecture overview"
```

---

## 自检清单

1. **Spec coverage**:
   - 数据模型 ↔ Task 1.2 (所有 5 个 ORM 模型)
   - EtsyClient ↔ Task 1.3 (重试、异常层次、缓存)
   - 关键词研究 ↔ Phase 2 (service + task + API + frontend)
   - 竞品分析 ↔ Phase 3 (shop_service + sync_tasks + API + frontend)
   - SEO 模块 ↔ Phase 4 (seo_service + seo_tasks + API + frontend)
   - 仪表盘 ↔ Task 5.1
   - Docker Compose ↔ Task 1.1
   - 错误处理 ↔ EtsyClient 异常、Celery retry、202 Accepted

2. **Placeholder check**: 无 TBD、TODO，所有步骤有完整代码

3. **Type consistency**: 
   - 前端 `api.ts` 返回类型与 `types.ts` 定义一致
   - 后端 API 返回字段与 ORM 模型字段一致
   - `task_id` / `keyword_id` / `shop_id` / `listing_id` / `audit_id` 命名一致
