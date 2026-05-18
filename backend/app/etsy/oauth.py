"""
Etsy OAuth 2.0 Authorization Code Grant + PKCE 流程。

PKCE 流程:
1. 生成 code_verifier (32随机字节 → url-safe base64, 去尾部=)
2. code_challenge = base64url(sha256(code_verifier)), 去尾部=
3. 构建授权 URL → 用户在浏览器中批准
4. 用授权码 + code_verifier 交换 access_token
5. access_token 1小时过期，用 refresh_token (90天) 续期

Shared secret 不参与 OAuth 2.0 token 交换。
"""

import base64
import hashlib
import secrets
from typing import Tuple

import httpx

ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"


def generate_code_verifier() -> str:
    """生成 PKCE code_verifier: 32字节随机 → url-safe base64, 去尾部=, 43-128字符"""
    token = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(token).rstrip(b"=").decode("ascii")


def generate_code_challenge(code_verifier: str) -> str:
    """从 code_verifier 生成 code_challenge = base64url(sha256(verifier)), 去尾部="""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_pkce_pair() -> Tuple[str, str]:
    """生成 (code_verifier, code_challenge) 对"""
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    return verifier, challenge


def generate_state(length: int = 32) -> str:
    """生成 CSRF 防护 state 随机字符串"""
    return secrets.token_urlsafe(length)


def build_authorization_url(
    client_id: str,
    redirect_uri: str,
    scopes: str,
    state: str,
    code_challenge: str,
) -> str:
    """构建 Etsy OAuth 授权 URL (Step 1: 请求授权码)"""
    from urllib.parse import urlencode

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{ETSY_AUTH_URL}?{urlencode(params)}"


def _get_proxy() -> str | None:
    from app.config import settings
    return settings.etsy_proxy_url or None


async def exchange_code_for_token(
    client_id: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
) -> dict:
    """Step 3: 用授权码交换 access token (POST x-www-form-urlencoded)"""
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code": code,
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient(proxy=_get_proxy()) as client:
        resp = await client.post(ETSY_TOKEN_URL, data=data)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Token exchange failed (HTTP {resp.status_code}): {resp.text}"
            )
        return resp.json()


async def refresh_access_token(
    client_id: str,
    refresh_token: str,
) -> dict:
    """使用 refresh token 获取新的 access token (POST x-www-form-urlencoded)"""
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(proxy=_get_proxy()) as client:
        resp = await client.post(ETSY_TOKEN_URL, data=data)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Token refresh failed (HTTP {resp.status_code}): {resp.text}"
            )
        return resp.json()
