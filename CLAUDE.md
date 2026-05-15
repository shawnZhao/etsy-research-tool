# Etsy Research Tool - Project Context

> 最后更新: 2026-05-15 | Phase 1-3 完成 | 当前: 开始 Phase 4

## 项目定位

面向 Etsy 卖家的市场调研工具，关键词研究 + 竞品分析 + 商品 SEO。先内部使用，后 SaaS 化。

## 核心文档

- **设计规格书:** `docs/superpowers/specs/2026-05-15-etsy-research-tool-design.md`
- **实施计划书:** `docs/superpowers/plans/2026-05-15-etsy-research-tool-plan.md`

**所有实现必须严格遵循这两个文档。** 不自行发挥架构设计，不跳过计划中的任务步骤。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 + FastAPI |
| 前端 | TypeScript + Next.js (App Router) + Tailwind |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 async |
| 任务队列 | Celery + Redis |
| 部署 | Docker Compose |

## 当前项目状态

### Phase 1 ✅ — 项目骨架
- Docker Compose (postgres, redis, backend, worker, frontend)
- FastAPI entry, CORS, health check, lifespan handler
- 5 个 ORM 模型: Keyword, Shop, Listing, RankingSnapshot, SEOAudit
- AsyncSession + get_db 依赖注入
- EtsyClient (httpx, retry, error hierarchy, auth)
- Celery 配置 (JSON serialization, acks_late, connection retry)
- 前端 layout (导航栏), types.ts (12 个接口), api.ts (18 个 API 函数)

### Phase 2 ✅ — 关键词研究模块
- KeywordService: 搜索量估算, 竞争度评分, 标签提取, 趋势计算
- Celery 任务: search_and_analyze_keyword (Etsy 搜索 → 分析 → 存储)
- API 端点: POST /search, GET /, GET /{id}, GET /{id}/related, POST /compare, GET /{id}/trend
- API 端点: GET /tasks/{task_id} (Celery 任务状态)
- 前端: 关键词列表页 (搜索框 + 卡片) + 关键词详情页 (指标 + 标签 + 趋势)

### Phase 3 ✅ — 竞品分析模块
- ShopService: upsert_shop, analyze_tags (top 50), analyze_categories (top 10 + pct), analyze_prices (min/max/avg/median)
- Celery 任务: sync_shop (fetch shop + paginate listings + run analysis), _upsert_listing helper
- EtsyClient: find_shop (shop name → numeric ID resolution)
- API 端点: POST /shops/track, GET /shops/, GET /shops/{id}, GET /shops/{id}/tags, GET /shops/{id}/listings, GET /shops/{id}/trend, POST /shops/compare
- 前端: 竞品列表页 (URL 输入 + Track Shop + 轮询状态) + 店铺详情页 (指标卡片 + 标签云 + 品类分布 + 最近 listing)
- types.ts: Shop.last_synced → last_updated 修复

### Phase 4 ⏳ — 商品 SEO 模块 (下一步)
### Phase 5 ⏳ — 仪表盘整合 + UI 打磨

## 关键架构决策

1. **所有 Etsy API 调用走 Celery 异步任务** — 前端请求即时返回 task_id，轮询获取结果
2. **EtsyClient 独立适配层** — httpx.AsyncClient, base_url="https://openapi.etsy.com/v3/", path 不带前导 /
3. **数据写 PostgreSQL 预计算** — 分析结果(评分、标签、趋势)离线算好存入 DB，前端直接查
4. **JSONB 存 Etsy 原始数据** — 每个模型有 etsy_raw 字段保留 API 原始返回
5. **UUID 主键** — 所有表用 UUID，通过 UUIDMixin 提供
6. **API 请求用 Pydantic 模型** — 不裸用 str/int 参数

## 实施规则 (CRITICAL)

1. **严格按计划书执行** — 每任务对应计划书中一个 Task，不跳过不合并
2. **Subagent-Driven Development** — 实施员 → spec compliance review → code quality review，缺一不可
3. **先审后进** — 每个任务的两轮审查必须通过才能进入下一个任务
4. **所有审查发现的问题必须修复** — Critical/Important 问题修复后才算任务完成
5. **遵循已有代码模式** — 新增代码必须与现有文件风格一致
6. **不引入计划外依赖** — 不添加 requirements.txt/package.json 中未列出的包

## 文件结构 (当前源码)

```
backend/app/
├── main.py              # FastAPI 入口, 路由挂载, lifespan
├── config.py             # pydantic-settings, etsy_api_base_url="https://openapi.etsy.com/v3/"
├── api/
│   ├── keywords.py       # /api/keywords/* (6 endpoints)
│   ├── shops.py          # /api/shops/* (7 endpoints)
│   └── tasks.py          # /api/tasks/{task_id}
├── models/
│   ├── keyword.py        # Keyword (keyword, volume, competition, tags, trend)
│   ├── shop.py           # Shop (shop_id, name, tags_used, category_dist, price_range)
│   ├── listing.py        # Listing (listing_id, FK→shops.shop_id, title, tags, price)
│   ├── ranking.py        # RankingSnapshot (FK→listings, FK→keywords, position)
│   └── seo_audit.py      # SEOAudit (FK→listings, title/tag/desc scores, suggestions)
├── services/
│   ├── keyword_service.py # KeywordService (5 methods)
│   └── shop_service.py    # ShopService (4 methods)
├── etsy/
│   ├── client.py         # EtsyClient (httpx, retry 3x, _handle_response, 6 endpoints incl. find_shop)
│   ├── auth.py           # EtsyAuth (x-api-key + Bearer token)
│   └── exceptions.py     # EtsyAPIError hierarchy (5 classes)
├── tasks/
│   ├── celery_app.py     # Celery 配置 (acks_late, retry_on_startup, result_expires)
│   ├── keyword_tasks.py  # search_and_analyze_keyword
│   └── sync_tasks.py     # sync_shop + _upsert_listing
└── db/
    ├── base.py           # Base, UUIDMixin, TimestampMixin
    └── session.py        # async_session, get_db()

frontend/src/
├── app/
│   ├── layout.tsx        # 导航栏 (/, /keywords, /shops, /seo)
│   ├── page.tsx          # 首页 (Next.js boilerplate, 等待 Phase 5 替换)
│   ├── keywords/
│   │   ├── page.tsx      # 关键词列表 (搜索框, 轮询 task 状态, 卡片 grid)
│   │   └── [id]/page.tsx # 关键词详情 (指标卡片, 关联标签, 趋势历史)
│   └── shops/
│       ├── page.tsx      # 竞品列表 (URL输入, Track Shop, 轮询状态)
│       └── [id]/page.tsx # 店铺详情 (指标, 标签云, 品类分布, listing)
└── lib/
    ├── types.ts          # 12 个接口 (Shop.last_updated 已修正)
    └── api.ts            # request<T> 泛型封装, 18 个 API 函数
```

## 关键模式与约定

### 后端
- AsyncSession 通过 FastAPI `Depends(get_db)` 注入
- Service 类接收 `db: AsyncSession` 构造参数
- ORM 模型用 `Mapped[]` 类型标注, JSONB 列区分 `Mapped[list]` vs `Mapped[dict]`
- Numeric 列用 `Mapped[Decimal]` 而非 `Mapped[float]`
- Celery 任务: sync outer function `def task(self, ...)` 内用 `asyncio.run(_run())`
- 任务用 `self.retry(exc=exc)` 触发重试, `bind=True` 必须
- EtsyClient 路径: path 先 lstrip("/"), 因为 base_url 以 / 结尾

### 前端
- 使用相对路径导入 (无 @/ alias)
- "use client" 声明客户端组件
- 页面: useState + useEffect 模式, loading/error/empty 三种状态都要处理
- API 调用通过 `@/lib/api` (实际用相对路径) 中的函数
- TaskStatus.status 值: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" (Celery 大写)

## 不做的
- 不爬取 Etsy 网页
- 不做用户认证系统 (SaaS 阶段)
- 不做 i18n
- 不做实时数据推送
- 不添加计划外的功能
