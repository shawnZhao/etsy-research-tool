# Etsy 调研工具 — 设计规格书

> 状态: 草稿 | 日期: 2026-05-15

## 概述

面向 Etsy 卖家的市场调研工具，首个版本聚焦三个核心模块：关键词研究、竞品分析、商品 SEO。供小团队内部使用，架构设计上为未来 SaaS 化预留扩展性。

**数据来源**：Etsy Open API v3，纯 API 方案，不做网页爬取。

---

## 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| 后端 | Python 3.12 + FastAPI | 数据处理生态好，异步支持成熟 |
| 前端 | TypeScript + Next.js 14 (App Router) | 仪表盘类组件丰富，开发效率高 |
| 数据库 | PostgreSQL 16 | 关系型 + JSONB 灵活存储 |
| 任务队列 | Celery + Redis | 数据采集全部异步化 |
| 缓存 | Redis | 搜索结果缓存，减少 Etsy API 调用 |
| ORM | SQLAlchemy 2.0 (async) | 与 FastAPI 搭配最成熟 |
| 迁移 | Alembic | SQLAlchemy 标配 |
| 前端图表 | Tremor (基于 Recharts) | 专为仪表盘设计，React 原生 |
| 部署 | 初期单机 Docker Compose | SaaS 化后迁移到 K8s |

## 不做的事

- 不爬取 Etsy 网页（法律风险 + 维护成本）
- 不做实时数据（Etsy API 做不到，也没必要）
- 不做浏览器扩展
- 不接入支付/计费系统（SaaS 阶段再做）
- 不做多语言 i18n（内部工具不需要）

---

## 系统架构

### 分层架构图

```
┌─────────────────────────────────────────────┐
│              Next.js 前端                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │关键词研究 │ │ 竞品分析  │ │ 商品SEO  │     │
│  └──────────┘ └──────────┘ └──────────┘     │
└──────────────────┬──────────────────────────┘
                   │ REST API (JSON)
┌──────────────────▼──────────────────────────┐
│           FastAPI 后端                       │
│                                              │
│  ┌──────────┐ ┌──────────────────────────┐  │
│  │ API 路由  │ │   Celery Workers          │  │
│  │ /keyword │ │   ├── sync_shop           │  │
│  │ /shop    │ │   ├── search_keyword      │  │
│  │ /listing │ │   ├── analyze_seo         │  │
│  │ /seo     │ │   └── track_ranking       │  │
│  └────┬─────┘ └────────────┬─────────────┘  │
│       │                    │                  │
│  ┌────▼────────────────────▼──────────────┐  │
│  │           服务层                        │  │
│  │  KeywordService                       │  │
│  │  ShopService                          │  │
│  │  ListingService                       │  │
│  │  SEOService                           │  │
│  │  EtsyClient (API 适配器)              │  │
│  └────┬───────────────────────────────────┘  │
│       │                                       │
│  ┌────▼────────┐  ┌──────────────────────┐  │
│  │  EtsyClient │  │  数据仓库层           │  │
│  │  (httpx)    │  │  PostgreSQL + Redis   │  │
│  └─────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────┘
```

### EtsyClient 设计

独立的 Etsy API 适配器，封装所有与 Etsy 的通信：

```python
class EtsyClient:
    """Etsy API v3 客户端，处理认证、限流、重试、结果缓存"""

    async def search_listings(keyword, limit, offset, sort) -> list[ListingRaw]
    async def get_listing(listing_id) -> ListingRaw
    async def get_shop(shop_id) -> ShopRaw
    async def get_shop_listings(shop_id, page) -> list[ListingRaw]
    async def get_listing_reviews(listing_id, page) -> list[ReviewRaw]
    async def get_categories() -> list[CategoryRaw]
```

关键行为：
- 所有方法使用 `httpx.AsyncClient` 连接池复用
- 自动处理 OAuth token 刷新
- 遇到 429 自动退避重试（指数退避，最多 3 次）
- 搜索结果带 Redis 缓存（TTL: 1 小时），减少重复 API 调用
- 所有 API Error 统一转换为自定义异常，上层不用关心 Etsy 细节

### 数据流总览

```
用户请求 ──→ FastAPI 路由 ──→ 查 PostgreSQL/Redis ──→ 即时返回
                │
                └──→ 触发 Celery 任务
                         └──→ EtsyClient ──→ Etsy API
                                  │
                                  └──→ 写入 PostgreSQL
                                  └──→ 通知前端 (WebSocket/轮询)
```

---

## 数据模型

### Keyword（关键词）

```python
class Keyword(Base):
    __tablename__ = "keywords"

    id: UUID (PK)
    keyword: str (UNIQUE, INDEX)
    search_volume_est: int          # 估算搜索量（基于搜索结果数）
    competition_score: float        # 竞争度评分 0-100（自算）
    avg_price: Decimal              # 搜索结果均价
    listing_count: int              # 搜索结果数量
    top_category: str               # 主要类目
    related_tags: JSONB             # 相关高频标签 [{tag, count}]
    trend_direction: str            # up / down / stable
    trend_data: JSONB               # 历史搜索量快照 [{date, volume}]
    etsy_raw: JSONB                 # 最后一次 Etsy API 搜索原始返回
    last_updated: datetime
    created_at: datetime
```

### Shop（店铺）

```python
class Shop(Base):
    __tablename__ = "shops"

    id: UUID (PK)
    shop_id: int (UNIQUE, INDEX)     # Etsy shop ID
    name: str
    url: str
    total_listings: int
    total_reviews: int
    avg_rating: Decimal
    tags_used: JSONB                 # 使用过的所有标签统计 [{tag, count}]
    category_distribution: JSONB     # 品类分布 [{category, count, pct}]
    price_range: JSONB               # {min, max, avg, median}
    listing_frequency: JSONB         # 上架频率分析
    etsy_raw: JSONB                  # Etsy API 原始返回
    last_synced: datetime
    created_at: datetime
```

### Listing（商品）

```python
class Listing(Base):
    __tablename__ = "listings"

    id: UUID (PK)
    listing_id: int (UNIQUE, INDEX)
    shop_id: FK → Shop
    title: str
    description: str
    tags: JSONB                      # ["tag1", "tag2", ...] 最多13个
    price: Decimal
    currency: str
    category: str
    category_path: JSONB             # ["一级", "二级", "三级"]
    url: str
    images: JSONB                    # [url1, url2, ...]
    favorites: int
    review_count: int
    rating: Decimal
    views_est: int                   # 基于 favorites/reviews 估算
    etsy_raw: JSONB
    last_updated: datetime
    created_at: datetime
```

### RankingSnapshot（排名快照）

```python
class RankingSnapshot(Base):
    __tablename__ = "ranking_snapshots"

    id: UUID (PK)
    listing_id: FK → Listing
    keyword_id: FK → Keyword
    position: int                    # 搜索结果中的排名
    total_results: int               # 当时的总搜索结果数
    captured_at: datetime
```

### SEOAudit（SEO 审计）

```python
class SEOAudit(Base):
    __tablename__ = "seo_audits"

    id: UUID (PK)
    listing_id: FK → Listing
    title_score: float               # 0-100
    tag_score: float                 # 0-100
    description_score: float         # 0-100
    overall_score: float             # 0-100
    suggestions: JSONB               # [{type, severity, message, detail}]
    benchmarks: JSONB                # 同类目 TopN 平均值
    created_at: datetime
```

### User（用户 — SaaS 阶段启用）

当前版本不实现用户系统。MVP 阶段单用户，数据直接查询。SaaS 化时通过 `owner_id` 隔离数据。

---

## 模块设计

### 模块一：关键词研究

**功能列表**：
- 搜索任意关键词，获取分析结果
- 展示：估算搜索量、竞争度、均价、商品数量、趋势方向
- 搜索量 vs 竞争度气泡图（可视化选词空间）
- 从当前关键词提取相关长尾词推荐
- 关键词对比表（多选几个词并列对比）
- 趋势历史（反复搜索同一关键词时记录历史）

**API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/keywords/search` | 搜索关键词，触发后台分析 |
| GET | `/api/keywords/{id}` | 获取关键词分析结果 |
| GET | `/api/keywords?sort=volume&order=desc` | 已分析关键词列表 |
| GET | `/api/keywords/{id}/related` | 获取关联长尾词 |
| POST | `/api/keywords/compare` | 批量对比关键词 |
| GET | `/api/keywords/{id}/trend` | 关键词趋势数据 |

**核心算法**：

```
搜索量估算:
  volume_est = search_result_count × category_weight
  - search_result_count: Etsy 搜索返回的 total_count
  - category_weight: 类目热度系数（基于类目总商品数归一化）

竞争度评分:
  competition = (
    0.4 × (high_sales_listings / top_100) +
    0.3 × (avg_review_count / max_review_count) +
    0.3 × (1 - avg_price_dispersion)
  ) × 100

长尾词推荐:
  1. 取搜索结果 Top 50 商品的 tags
  2. 统计 tag 共现频率
  3. 与原关键词一起做 N-gram 组合
  4. 去重，按频率排序，取 Top 20
```

### 模块二：竞品分析

**功能列表**：
- 添加竞品店铺（输入 Etsy 店铺 URL 或名称）
- 店铺概览仪表盘（商品数、评价、评分、上架频率）
- 标签策略分析（高频标签词云 + 标签组合模式）
- 价格带分布图
- 品类分布饼图
- 新品监控（最近 30 天上架商品趋势）
- 多店铺并排对比表

**API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/shops/track` | 添加/开始追踪一个店铺 |
| GET | `/api/shops` | 所有追踪中的店铺 |
| GET | `/api/shops/{id}` | 店铺详情 + 分析 |
| GET | `/api/shops/{id}/tags` | 标签分析数据 |
| GET | `/api/shops/{id}/listings` | 店铺商品列表（分页） |
| GET | `/api/shops/{id}/trend` | 店铺指标趋势 |
| POST | `/api/shops/compare` | 多店铺对比 |

**核心分析逻辑**：

```
标签策略提取:
  1. 拉取店铺所有 Listing 的 tags
  2. 统计每个 tag 的使用频率
  3. 识别标签组合模式（哪些标签经常一起出现）
  4. 输出：高频标签 Top 20 + 推荐标签组合

上架频率:
  从 Listing.created_at 聚合统计，输出周/月粒度上架趋势
```

### 模块三：商品 SEO

**功能列表**：
- 输入自己的 Listing URL，生成 SEO 审计报告
- 标题评分：长度、核心词出现位置、可读性
- 标签评分：是否用满 13 个、长尾词占比、与标题的一致性
- 描述评分：关键词密度、结构化程度
- 缺失标签推荐（基于同类目 Top 商品）
- 标题优化建议
- 与同类目 Top 10 商品对比

**API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/seo/audit` | 对指定 Listing 执行 SEO 审计 |
| GET | `/api/seo/audits/{id}` | 获取审计报告 |
| GET | `/api/seo/audits?listing_id=X` | 某商品的审计历史 |
| GET | `/api/seo/suggestions/{listing_id}` | 获取优化建议 |
| GET | `/api/seo/benchmarks?category=X` | 类目基准数据 |

**SEO 评分算法**：

```
标题评分 (0-100):
  - 长度 40-60 字符: 30 分
  - 核心关键词在前 40 字符: 30 分
  - 无全大写/无关键词堆砌: 20 分
  - 包含 2+ 长尾修饰词: 20 分

标签评分 (0-100):
  - 使用 13/13 标签: 25 分
  - 包含 3+ 长尾标签: 25 分
  - 标签与标题关键词一致: 25 分
  - 使用类目热门标签: 25 分

描述评分 (0-100):
  - 长度 > 200 字符: 25 分
  - 核心关键词出现 2-4 次: 25 分
  - 结构化（分段/列表）: 25 分
  - 包含 2+ 长尾关键词: 25 分

总体评分 = 标题 × 0.35 + 标签 × 0.40 + 描述 × 0.25
```

---

## 错误处理策略

### Etsy API 层

```
EtsyAPIError (基类)
├── EtsyRateLimitError (429) → 自动退避重试，3次后放弃
├── EtsyAuthError (401/403) → 告警，需要手动处理
├── EtsyNotFoundError (404) → 正常情况（商品下架等），标记数据过期
└── EtsyServerError (5xx) → 退避重试，3次后标记任务失败
```

### Celery 任务层

- 所有任务定义 `max_retries=3`，使用指数退避
- 任务失败记录到 `task_errors` 表，前端可展示同步状态
- 同一 Etsy 资源避免并发同步（Redis 分布式锁）

### API 层

- 统一错误响应格式 `{error: {code, message, detail}}`
- 数据库查询不到返回 404 不报 500
- 后台任务未完成时返回状态码 `202 Accepted` + `{status: "processing"}`

---

## 项目结构

```
etsy-research/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置（环境变量）
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── keywords.py         # /api/keywords 路由
│   │   │   ├── shops.py            # /api/shops 路由
│   │   │   ├── listings.py         # /api/listings 路由
│   │   │   └── seo.py              # /api/seo 路由
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── keyword.py
│   │   │   ├── shop.py
│   │   │   ├── listing.py
│   │   │   ├── ranking.py
│   │   │   └── seo_audit.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── keyword_service.py
│   │   │   ├── shop_service.py
│   │   │   ├── listing_service.py
│   │   │   └── seo_service.py
│   │   ├── etsy/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # EtsyClient 实现
│   │   │   ├── auth.py             # OAuth 管理
│   │   │   └── exceptions.py       # Etsy 异常定义
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py       # Celery 配置
│   │   │   ├── sync_tasks.py       # 店铺/商品同步任务
│   │   │   ├── keyword_tasks.py    # 关键词分析任务
│   │   │   └── seo_tasks.py        # SEO 审计任务
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── session.py          # async session factory
│   │       └── base.py             # declarative base
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # 首页 / 导航
│   │   │   ├── keywords/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── shops/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   └── seo/
│   │   │       ├── page.tsx
│   │   │       └── [id]/page.tsx
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   ├── tables/
│   │   │   └── layout/
│   │   └── lib/
│   │       ├── api.ts              # API 调用封装
│   │       └── types.ts
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 依赖服务配置

### docker-compose.yml 服务清单

| 服务 | 镜像 | 用途 |
|------|------|------|
| backend | 自构建 | FastAPI 应用 |
| frontend | 自构建 | Next.js 开发模式 |
| worker | 自构建 | Celery worker |
| postgres | postgres:16 | 主数据库 |
| redis | redis:7-alpine | 消息队列 + 缓存 |

---

## 待明确事项

以下内容需要在实现前确定，当前设计设定了默认选项：

1. **Etsy API Key 申请** — 需要去 developers.etsy.com 注册应用。MVP 阶段用个人 API Key，SaaS 阶段需要 OAuth 流程。**默认**：先跑通个人 Key
2. **关键词搜索量精算** — Etsy API 不提供搜索量。**默认**：用搜索结果数 × 类目系数估算，积累历史数据后可拟合更准的模型
3. **排名追踪频率** — 多久刷新一次排名快照。**默认**：每天一次（Etsy 排名波动慢，不需要高频）

---

## 开发顺序

| 阶段 | 内容 | 预计产出 |
|------|------|---------|
| Phase 1 | 项目骨架 + EtsyClient + 数据库 | 能连上 Etsy API，跑通第一个查询 |
| Phase 2 | 关键词研究模块 | 搜索关键词 → 展示分析结果 |
| Phase 3 | 竞品分析模块 | 追踪店铺 → 标签/价格/品类分析 |
| Phase 4 | 商品 SEO 模块 | SEO 审计 → 评分 + 建议 |
| Phase 5 | 仪表盘整合 + UI 打磨 | 统一导航，数据可视化完善 |

---

## 后续演进（SaaS 化预留）

- 用户注册/登录 + 数据隔离（`owner_id`）
- API 调用额度管理（每个用户每日限额）
- 计费系统集成（Stripe）
- 邮件通知（排名变化、竞品上新）
- Etsy OAuth 集成（用户授权访问自己的店铺数据）
