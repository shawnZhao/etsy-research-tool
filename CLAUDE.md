# Etsy Research Tool - Project Context

> 最后更新: 2026-05-18 | Phase 1-6 全部完成

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
| 前端 | TypeScript + Next.js 16 (App Router) + Tailwind CSS 4 |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 async |
| 任务队列 | Celery + Redis |
| 认证 | Etsy OAuth 2.0 PKCE (Redis-backed token management) |
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

### Phase 4 ✅ — 商品 SEO 模块
- SEOService: 纯函数评分算法 — score_title (长度/关键字位置/大小写/修饰词), score_tags (槽位/长尾词/标题对齐/热词), score_description (长度/关键词密度/结构/长尾短语)
- 辅助: extract_core_keywords (前5标题词+前3标签, 去重max5), compute_overall_score (35/40/25权重)
- 修复: 词边界匹配 (\b) 避免子串误判 (gold≠golden), 标题词标点清理
- Celery 任务: run_seo_audit (fetch listing → upsert → score → save SEOAudit)
- API 端点: POST /seo/audit, GET /seo/audits/{id}, GET /seo/audits, GET /seo/benchmarks
- EtsyClient: get_listing 返回单个 listing dict (非包裹在 results 中)
- 前端: SEO 列表页 (URL输入 + Audit按钮 + 轮询 + ScoreBadge/ScoreBar) + SEO 详情页 (总评分 + ScoreCircle + 改进建议卡片)
- 修复: 搜索/审计按钮 Enter 键并发守卫 (keywords + seo 页面)

### Phase 5 ✅ — 仪表盘整合 + UI 打磨
- Dashboard 首页: 3 个统计卡片 (Keywords/Shops/SEO) + 最近关键词 top 5 + 追踪店铺 top 5
- 全局路由挂载: main.py 挂载所有 22 个 API 端点 + 健康检查 + OAuth 认证
- Alembic 初始迁移: 0001_initial.py 覆盖全部 5 个表
- 类型提示修复: Optional[X] 替代 X | None (Python 3.9+ 兼容)
- README.md: 快速开始、架构概览、开发命令、模块说明

### Phase 6 ✅ — 生产加固 + 双语支持
- **BigInteger 迁移**: Etsy shop_id/listing_id 从 Integer → BigInteger，适配大数值 ID
- **线程安全引擎**: async engine/session + Redis 连接加 event loop 检测，适配多线程 Celery worker
- **SEO 查询优化**: selectinload 预加载 Listing 关联，避免 N+1 查询
- **国际 URL 支持**: 店铺追踪正则兼容 `etsy.com/hk-en/shop/NAME` 等国际化 URL
- **同步性能**: 店铺 listing 同步上限 500 条，防止分页耗时过长
- **空值防护**: Etsy API 返回字段（tags, images, taxonomy_path）防御性处理 null 值
- **双语支持 (EN/中文)**: React Context + JSON 字典 + localStorage 持久化，零外部依赖
- **字段注释**: InfoBadge + Tooltip 组件，详情页指标旁 "?" 图标 hover 展示字段含义，双语切换
- **共享组件**: Navbar, Tooltip, InfoBadge, LanguageSwitcher 提取为独立组件
- **README 更新**: 技术栈版本号、OAuth 认证、双语功能、项目结构、架构图

## 关键架构决策

1. **所有 Etsy API 调用走 Celery 异步任务** — 前端请求即时返回 task_id，轮询获取结果
2. **EtsyClient 独立适配层** — httpx.AsyncClient, base_url="https://openapi.etsy.com/v3/", path 不带前导 /
3. **数据写 PostgreSQL 预计算** — 分析结果(评分、标签、趋势)离线算好存入 DB，前端直接查
4. **JSONB 存 Etsy 原始数据** — 每个模型有 etsy_raw 字段保留 API 原始返回
5. **UUID 主键** — 所有表用 UUID，通过 UUIDMixin 提供
6. **API 请求用 Pydantic 模型** — 不裸用 str/int 参数
7. **轻量级 i18n** — React Context + JSON 字典 + localStorage，不引入 i18n 框架依赖
8. **前端组件提取** — 共享 UI 组件放入 `src/components/`，页面内私有组件保持内联

## 沟通约定

- **始终使用中文沟通** — 所有回复、解释、审查意见、提交信息均使用中文

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
│   ├── auth.py           # /api/auth/etsy/* (OAuth 授权 + 回调)
│   ├── keywords.py       # /api/keywords/* (6 endpoints)
│   ├── shops.py          # /api/shops/* (7 endpoints)
│   ├── seo.py            # /api/seo/* (4 endpoints, selectinload 预加载)
│   └── tasks.py          # /api/tasks/{task_id}
├── models/
│   ├── keyword.py        # Keyword (keyword, volume, competition, tags, trend)
│   ├── shop.py           # Shop (BigInteger shop_id, name, tags_used, category_dist, price_range)
│   ├── listing.py        # Listing (BigInteger listing_id/shop_id, FK→shops.shop_id, title, tags, price)
│   ├── ranking.py        # RankingSnapshot (FK→listings, FK→keywords, position)
│   └── seo_audit.py      # SEOAudit (FK→listings, relationship("Listing"), title/tag/desc scores, suggestions)
├── services/
│   ├── keyword_service.py # KeywordService (5 methods)
│   ├── shop_service.py    # ShopService (4 methods)
│   └── seo_service.py     # SEOService (5 pure methods, 词边界匹配)
├── etsy/
│   ├── client.py         # EtsyClient (httpx, retry 3x, _handle_response, 6 endpoints incl. find_shop)
│   ├── auth.py           # TokenManager (Redis-backed, event loop 检测, 分布式锁刷新)
│   ├── oauth.py          # PKCE 工具函数 (code_verifier/code_challenge 生成)
│   └── exceptions.py     # EtsyAPIError hierarchy (5 classes)
├── tasks/
│   ├── celery_app.py     # Celery 配置 (acks_late, retry_on_startup, result_expires)
│   ├── keyword_tasks.py  # search_and_analyze_keyword
│   ├── sync_tasks.py     # sync_shop (max 500 listings) + _upsert_listing (null-safe fields)
│   └── seo_tasks.py      # run_seo_audit + _get_or_create_listing (null-safe fields)
└── db/
    ├── base.py           # Base, UUIDMixin, TimestampMixin
    └── session.py        # _get_async_session() (event loop 检测), get_db(), get_engine()

frontend/src/
├── app/
│   ├── layout.tsx        # Server component: TranslationProvider + Navbar + main
│   ├── page.tsx          # Dashboard 首页 (统计卡片, 最近关键词, 追踪店铺, i18n)
│   ├── keywords/
│   │   ├── page.tsx      # 关键词列表 (搜索框, 轮询 task, 卡片 grid, i18n)
│   │   └── [id]/page.tsx # 关键词详情 (MetricCard + InfoBadge + 关联标签 + 趋势, i18n)
│   ├── shops/
│   │   ├── page.tsx      # 竞品列表 (URL输入, Track Shop, 轮询, i18n)
│   │   └── [id]/page.tsx # 店铺详情 (MetricCard + InfoBadge + 标签云 + 品类分布 + listing, i18n)
│   └── seo/
│       ├── page.tsx      # SEO 列表 (URL输入, Audit按钮, 轮询, ScoreBadge/Bar, i18n)
│       └── [id]/page.tsx # SEO 详情 (ScoreCircle + InfoBadge + 改进建议卡片, i18n)
├── components/
│   ├── Navbar.tsx         # 导航栏 + LanguageSwitcher (brand, 3 nav links, 语言切换按钮)
│   ├── Tooltip.tsx        # 纯 CSS hover tooltip (group/focus-within, 自适应定位)
│   ├── InfoBadge.tsx      # 标签 + "?" 图标 + tooltip 组合
│   └── LanguageSwitcher.tsx # EN/中文 切换按钮 (localStorage 持久化)
└── lib/
    ├── types.ts          # 12 个接口 (SEOAudit.listing 可选嵌套)
    ├── api.ts            # request<T> 泛型封装, 18 个 API 函数
    ├── annotations.ts    # 字段名 → 注释 i18n key 注册表 (13 个字段)
    └── i18n/
        ├── types.ts      # Locale, TranslationParams, TranslationDictionary
        ├── context.tsx   # TranslationProvider + useTranslation() hook + localStorage
        └── dictionaries/
            ├── en.json   # 英文翻译字典 (~90 条, 含 annotation.* 注释)
            └── zh.json   # 中文翻译字典 (~90 条, 含 annotation.* 注释)
```

## 关键模式与约定

### 后端
- AsyncSession 通过 FastAPI `Depends(get_db)` 注入；Celery 任务通过 `_get_async_session()` 获取
- Engine 创建使用 event loop 检测 (`get_running_loop()`)，适配多线程 worker 环境
- Service 类接收 `db: AsyncSession` 构造参数
- ORM 模型用 `Mapped[]` 类型标注, JSONB 列区分 `Mapped[list]` vs `Mapped[dict]`
- Numeric 列用 `Mapped[Decimal]` 而非 `Mapped[float]`
- Etsy ID 列用 `BigInteger` 而非 `Integer`（Etsy ID 可超 32 位）
- SEOAudit 查询使用 `selectinload(SEOAudit.listing)` 预加载关联 Listing
- Celery 任务: sync outer function `def task(self, ...)` 内用 `asyncio.run(_run())`
- 任务用 `self.retry(exc=exc)` 触发重试, `bind=True` 必须
- EtsyClient 路径: path 先 lstrip("/"), 因为 base_url 以 / 结尾
- Listing upsert 使用 `item.get("tags") or []` 防御性处理 Etsy API 返回的 null 字段

### 前端
- 使用相对路径导入 (无 @/ alias)
- "use client" 声明客户端组件（所有页面 + i18n context + 所有 components）
- 页面: useState + useEffect 模式, loading/error/empty 三种状态都要处理
- API 调用通过 `../lib/api` 中的函数
- TaskStatus.status 值: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" (Celery 大写)
- **i18n**: `useTranslation()` 返回 `{ t, locale, setLocale }`，`t(key, params?)` 支持 `{param}` 插值
- **i18n key 命名**: `{页面}.{元素}` 格式（如 `dashboard.title`, `keywords.list.searchButton`）
- **注释字段**: `getFieldAnnotation(fieldName)` → i18n key → 通过 `t()` 获取当前语言文本
- **共享组件**: 跨页面使用的 UI 组件放 `src/components/`，页面内私有组件保持内联
- **错误处理**: 存储原始错误消息，渲染时拼接翻译前缀（`t("prefix") + error`），语言切换时自动更新

## 不做的
- 不爬取 Etsy 网页
- 不做用户认证系统 (SaaS 阶段)
- 不做实时数据推送
- 不添加计划外的功能
