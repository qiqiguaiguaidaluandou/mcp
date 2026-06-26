"""统一鉴权模块：JWT 生成与缓存、登录换票据、带 401 自愈的请求原语。

所有需要 JWT 鉴权的工具都应通过这里取 token / 发请求，共享同一份缓存：
- 简单 JWT 鉴权（token 直接放 Authorization 头）的接口：用 `post_with_jwt`。
- 需要"JWT 换票据再调用"的接口（如 MES）：用 `get_ticket` 拿票据后再 `post_with_jwt`。

token / ticket 过期或被服务端拒绝（401/403）时，缓存会被清空并自动重试一次，
不会让一个坏 token 在整个 TTL 内毒化所有接口。
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone

import jwt

from mcpserver import config, http_client

_JWT_TTL_MINUTES = 60
_AUTH_REFRESH_BUFFER_SECONDS = 5 * 60

# JWT 公共缓存：所有需要 JWT 鉴权的接口共享这一份。
_jwt_cache: dict = {"token": None, "expires_at": 0.0}
_jwt_lock = asyncio.Lock()

# Ticket 缓存：仅"JWT 换票据"链路（如 MES）使用。
_ticket_cache: dict = {"ticket": None, "inv_org_id": None, "expires_at": 0.0}
_ticket_lock = asyncio.Lock()

_AUTH_FAIL_STATUS = (401, 403)


def _create_jwt_token() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": config.JWT_ISSUER,
        "exp": int((now + timedelta(minutes=_JWT_TTL_MINUTES)).timestamp()),
        "sub": "",
        "aud": "",
        "nbf": int((now - timedelta(minutes=10)).timestamp()),
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


async def _get_jwt_token() -> str:
    """返回缓存中的 JWT；不存在或已过期则本地重新生成并写回缓存。"""
    now = time.time()
    if _jwt_cache["token"] and now < _jwt_cache["expires_at"]:
        return _jwt_cache["token"]
    async with _jwt_lock:
        now = time.time()
        if _jwt_cache["token"] and now < _jwt_cache["expires_at"]:
            return _jwt_cache["token"]
        _jwt_cache["token"] = _create_jwt_token()
        _jwt_cache["expires_at"] = now + _JWT_TTL_MINUTES * 60 - _AUTH_REFRESH_BUFFER_SECONDS
        return _jwt_cache["token"]


def invalidate_jwt() -> None:
    """作废 JWT 缓存，下次取 token 时强制重新生成。"""
    _jwt_cache["expires_at"] = 0.0


def invalidate_ticket() -> None:
    """作废 ticket 缓存，下次取票据时强制重新登录。"""
    _ticket_cache["expires_at"] = 0.0


async def post_with_jwt(url: str, body: dict) -> dict:
    """带 JWT 鉴权发 POST 并返回 JSON。

    token 取自共享缓存。若服务端返回 401/403（视为 token 失效），清空 JWT 缓存
    并用新生成的 token 重试一次；仍失败则抛出 HTTP 异常。
    """
    client = http_client.get_client()
    for attempt in range(2):
        token = await _get_jwt_token()
        r = await client.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
        if r.status_code in _AUTH_FAIL_STATUS and attempt == 0:
            invalidate_jwt()
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("unreachable")  # 循环必在上面 return 或 raise


async def _login_for_ticket() -> tuple[str, int]:
    body = {
        "Parameters": [
            {"Value": config.LOGIN_USERNAME},
            {"Value": config.LOGIN_PASSWORD},
        ],
        "ApiType": "AuthenticationController",
        "Method": "Login",
        "Context": None,
    }
    data = await post_with_jwt(config.LOGIN_URL, body)
    if not data.get("Success"):
        raise RuntimeError(f"Login failed: {data.get('Message')}")
    ctx = data.get("Context") or {}
    ticket = ctx.get("Ticket")
    inv_org_id = ctx.get("InvOrgId")
    if not ticket or inv_org_id is None:
        raise RuntimeError("Login response missing Ticket or InvOrgId")
    return ticket, inv_org_id


async def get_ticket() -> tuple[str, int]:
    """返回缓存中的 (Ticket, InvOrgId)；不存在或已过期则用 JWT 重新登录换取。"""
    now = time.time()
    if _ticket_cache["ticket"] and now < _ticket_cache["expires_at"]:
        return _ticket_cache["ticket"], _ticket_cache["inv_org_id"]
    async with _ticket_lock:
        now = time.time()
        if _ticket_cache["ticket"] and now < _ticket_cache["expires_at"]:
            return _ticket_cache["ticket"], _ticket_cache["inv_org_id"]
        ticket, inv_org_id = await _login_for_ticket()
        _ticket_cache["ticket"] = ticket
        _ticket_cache["inv_org_id"] = inv_org_id
        _ticket_cache["expires_at"] = now + _JWT_TTL_MINUTES * 60 - _AUTH_REFRESH_BUFFER_SECONDS
        return ticket, inv_org_id
