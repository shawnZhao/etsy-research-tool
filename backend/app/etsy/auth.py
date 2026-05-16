"""
Etsy OAuth Token 管理 — 基于 Redis 存储，自动刷新。

Token 生命周期:
- access_token: Redis TTL 55分钟 (实际有效期1小时，提前5分钟刷新)
- refresh_token: Redis TTL 89天 (实际有效期90天)

首次认证: 访问 /api/auth/etsy/authorize 启动 OAuth PKCE 流程
"""

import asyncio
import logging

import redis.asyncio as aioredis

from app.config import settings
from app.etsy.oauth import refresh_access_token

logger = logging.getLogger(__name__)

REDIS_ACCESS_KEY = "etsy:access_token"
REDIS_REFRESH_KEY = "etsy:refresh_token"
REDIS_LOCK_KEY = "etsy:token:lock"

ACCESS_TOKEN_TTL = 3300       # 55 分钟
REFRESH_TOKEN_TTL = 7689600   # 89 天
LOCK_TIMEOUT = 10             # 刷新锁超时


class TokenManager:
    """基于 Redis 的 Etsy OAuth Token 管理器。

    每次获取 token 时先从 Redis 读；若已过期则用 refresh_token 自动续期。
    并发刷新由 Redis 分布式锁 + 本地 asyncio.Lock 双重保护。
    """

    def __init__(self):
        self._redis: aioredis.Redis | None = None
        self._local_lock = asyncio.Lock()

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def get_access_token(self) -> str:
        r = await self._get_redis()

        token = await r.get(REDIS_ACCESS_KEY)
        if token:
            return token

        return await self._refresh_or_bootstrap(r)

    async def _refresh_or_bootstrap(self, r: aioredis.Redis) -> str:
        async with self._local_lock:
            # 双重检查：等锁期间可能已被其他协程刷新
            token = await r.get(REDIS_ACCESS_KEY)
            if token:
                return token

            refresh = await r.get(REDIS_REFRESH_KEY)
            if not refresh and settings.etsy_refresh_token:
                # 首次启动：用 .env 中的 refresh_token 做 bootstrap
                refresh = settings.etsy_refresh_token

            if not refresh:
                raise RuntimeError(
                    "Etsy OAuth token 未配置。"
                    "请访问 /api/auth/etsy/authorize 完成首次认证。"
                )

            # 防止并发刷新，用 Redis 锁
            lock_ok = await r.set(REDIS_LOCK_KEY, "1", nx=True, ex=LOCK_TIMEOUT)
            if not lock_ok:
                # 别的进程正在刷新，轮询等待
                for _ in range(30):
                    await asyncio.sleep(1)
                    token = await r.get(REDIS_ACCESS_KEY)
                    if token:
                        return token
                raise RuntimeError("Token 刷新超时，请稍后重试")

            try:
                data = await refresh_access_token(
                    settings.etsy_api_key, refresh
                )
                access = data["access_token"]
                new_refresh = data["refresh_token"]
                expires_in = data["expires_in"]

                access_ttl = min(expires_in, ACCESS_TOKEN_TTL)
                await r.set(REDIS_ACCESS_KEY, access, ex=access_ttl)
                await r.set(REDIS_REFRESH_KEY, new_refresh, ex=REFRESH_TOKEN_TTL)

                logger.info("Etsy access token 已刷新，有效期 %ds", access_ttl)
                return access
            finally:
                await r.delete(REDIS_LOCK_KEY)

    async def save_tokens(self, access_token: str, refresh_token: str, expires_in: int):
        """首次 OAuth 认证后保存 token 到 Redis"""
        r = await self._get_redis()
        access_ttl = min(expires_in, ACCESS_TOKEN_TTL)
        await r.set(REDIS_ACCESS_KEY, access_token, ex=access_ttl)
        await r.set(REDIS_REFRESH_KEY, refresh_token, ex=REFRESH_TOKEN_TTL)
        logger.info("Etsy OAuth token 已保存到 Redis")


class EtsyAuth:
    def __init__(self):
        self.api_key = settings.etsy_api_key
        self._token_manager = TokenManager()

    async def get_headers(self) -> dict:
        access_token = await self._token_manager.get_access_token()
        return {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def save_tokens(self, access_token: str, refresh_token: str, expires_in: int):
        """供 OAuth 回调端点使用"""
        await self._token_manager.save_tokens(access_token, refresh_token, expires_in)


etsy_auth = EtsyAuth()
