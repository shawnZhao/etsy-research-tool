"""
Etsy OAuth 2.0 PKCE 认证端点。

首次使用流程:
1. 访问 /api/auth/etsy/authorize → 重定向到 Etsy 授权页
2. 用户在 Etsy 批准应用访问
3. Etsy 重定向回 /api/auth/etsy/callback?code=...&state=...
4. 后端自动交换 token，存入 Redis
5. 返回成功页面
"""

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.etsy.auth import etsy_auth
from app.etsy.oauth import (
    build_authorization_url,
    exchange_code_for_token,
    generate_pkce_pair,
    generate_state,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/etsy", tags=["auth"])

# OAuth 流程中的 state → (code_verifier, redirect_uri) 的 Redis key 前缀
OAUTH_STATE_PREFIX = "etsy:oauth:state:"
OAUTH_STATE_TTL = 600  # 10 分钟

# 默认值
DEFAULT_SCOPES = "listings_r shops_r transactions_r"
DEFAULT_REDIRECT_PATH = "/api/auth/etsy/callback"


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


@router.get("/authorize")
async def etsy_authorize(
    request: Request,
    redirect_uri: str | None = Query(
        None,
        description="回调 URL，默认基于当前请求构建",
    ),
    scopes: str | None = Query(
        None,
        description="Etsy API scopes，空格分隔。默认: listings_r shops_r transactions_r",
    ),
):
    """Step 1: 启动 OAuth PKCE 流程，重定向到 Etsy 授权页"""
    if not settings.etsy_api_key:
        raise HTTPException(500, "ETSY_API_KEY 未配置")

    if not redirect_uri:
        base = str(request.base_url).rstrip("/")
        redirect_uri = f"{base}{DEFAULT_REDIRECT_PATH}"
    if not scopes:
        scopes = DEFAULT_SCOPES

    code_verifier, code_challenge = generate_pkce_pair()
    state = generate_state()

    # 存储 state → (code_verifier, redirect_uri) 到 Redis
    r = await _get_redis()
    await r.setex(
        f"{OAUTH_STATE_PREFIX}{state}",
        OAUTH_STATE_TTL,
        f"{code_verifier}|{redirect_uri}",
    )

    auth_url = build_authorization_url(
        client_id=settings.etsy_api_key,
        redirect_uri=redirect_uri,
        scopes=scopes,
        state=state,
        code_challenge=code_challenge,
    )

    logger.info("OAuth 流程启动，state=%s...", state[:8])
    return RedirectResponse(auth_url)


@router.get("/callback")
async def etsy_callback(
    code: str = Query(..., description="Etsy 返回的授权码"),
    state: str = Query(..., description="Etsy 返回的 state"),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
):
    """Step 2: Etsy 回调，交换 token 并存入 Redis"""
    if error:
        raise HTTPException(
            400,
            f"Etsy 授权失败: {error} — {error_description or '无详细说明'}",
        )

    if not settings.etsy_api_key:
        raise HTTPException(500, "ETSY_API_KEY 未配置")

    # 验证 state 并取回 code_verifier
    r = await _get_redis()
    state_key = f"{OAUTH_STATE_PREFIX}{state}"
    stored = await r.get(state_key)
    if not stored:
        raise HTTPException(400, "OAuth state 无效或已过期，请重新发起授权")

    await r.delete(state_key)
    code_verifier, redirect_uri = stored.split("|", 1)

    # 交换 token
    try:
        token_data = await exchange_code_for_token(
            settings.etsy_api_key,
            redirect_uri,
            code,
            code_verifier,
        )
    except RuntimeError as e:
        logger.error("Token exchange failed: %s", e)
        raise HTTPException(500, f"Token 交换失败: {e}")

    # 存入 Redis (通过 auth 模块)
    await etsy_auth.save_tokens(
        token_data["access_token"],
        token_data["refresh_token"],
        token_data["expires_in"],
    )

    logger.info("OAuth 认证完成，token 已存储")

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"><title>认证成功</title>
        <style>
            body {{ font-family: system-ui; display: flex; justify-content: center;
                   align-items: center; min-height: 100vh; margin: 0;
                   background: #f5f5f5; }}
            .card {{ background: white; padding: 48px; border-radius: 12px;
                     box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; max-width: 420px; }}
            h1 {{ color: #2e7d32; margin: 0 0 12px; }}
            p {{ color: #666; margin: 0; }}
        </style></head>
        <body>
            <div class="card">
                <h1>✅ Etsy 认证成功</h1>
                <p>Token 已保存，API 调用现在可以正常工作了。</p>
            </div>
        </body></html>
        """
    )
