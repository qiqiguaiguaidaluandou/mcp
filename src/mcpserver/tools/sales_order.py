import asyncio
import time
from datetime import datetime, timedelta, timezone

import httpx
import jwt

from mcpserver import config


async def _fetch(sn: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(config.SEARCH_SN_IN_SALES_POST_ORDER_URL, json={"sn": sn})
        r.raise_for_status()
        return r.json()


_JWT_TTL_MINUTES = 60
_AUTH_REFRESH_BUFFER_SECONDS = 5 * 60
_auth_cache: dict = {"token": None, "ticket": None, "inv_org_id": None, "expires_at": 0.0}
_auth_lock = asyncio.Lock()


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


async def _login_for_ticket(token: str) -> tuple[str, int]:
    body = {
        "Parameters": [
            {"Value": config.LOGIN_USERNAME},
            {"Value": config.LOGIN_PASSWORD},
        ],
        "ApiType": "AuthenticationController",
        "Method": "Login",
        "Context": None,
    }
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(config.LOGIN_URL, json=body, headers=headers)
        r.raise_for_status()
        data = r.json()
    if not data.get("Success"):
        raise RuntimeError(f"Login failed: {data.get('Message')}")
    ctx = data.get("Context") or {}
    ticket = ctx.get("Ticket")
    inv_org_id = ctx.get("InvOrgId")
    if not ticket or inv_org_id is None:
        raise RuntimeError("Login response missing Ticket or InvOrgId")
    return ticket, inv_org_id


async def _get_auth_context() -> tuple[str, str, int]:
    now = time.time()
    if _auth_cache["token"] and now < _auth_cache["expires_at"]:
        return _auth_cache["token"], _auth_cache["ticket"], _auth_cache["inv_org_id"]
    async with _auth_lock:
        now = time.time()
        if _auth_cache["token"] and now < _auth_cache["expires_at"]:
            return _auth_cache["token"], _auth_cache["ticket"], _auth_cache["inv_org_id"]
        token = _create_jwt_token()
        ticket, inv_org_id = await _login_for_ticket(token)
        _auth_cache["token"] = token
        _auth_cache["ticket"] = ticket
        _auth_cache["inv_org_id"] = inv_org_id
        _auth_cache["expires_at"] = now + _JWT_TTL_MINUTES * 60 - _AUTH_REFRESH_BUFFER_SECONDS
        return token, ticket, inv_org_id


async def _fetch_repair_process(sn: str) -> dict:
    token, ticket, inv_org_id = await _get_auth_context()
    body = {
        "ApiType": "AiController",
        "Parameters": [{"Value": {"Sn": sn}}],
        "Method": "GetSN",
        "Context": {"Ticket": ticket, "InvOrgId": inv_org_id},
    }
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(config.GETSN_URL, json=body, headers=headers)
        r.raise_for_status()
        data = r.json()
    if not data.get("Success"):
        _auth_cache["expires_at"] = 0.0
        raise RuntimeError(f"GetSN failed: {data.get('Message')}")
    return data.get("Result", {})


def register(mcp):
    @mcp.tool()
    async def search_sn_in_sales_post_order_count(sn: str) -> int:
        """统计某台机器在 CRM 系统中的售后维修/服务工单总数。

        适用场景：用户想知道"这台机器修过几次"、"维修次数"、"返修频率"、
        "有没有售后记录"等只关心数量、不关心具体内容的问题。
        如果用户想看维修详情，请改用 search_sn_in_sales_post_order_data。

        Args:
            sn: 机器序列号（Serial Number），通常为厂商出厂时打在机身上的
                唯一编号。直接传入用户提供的原始字符串即可，不要做大小写
                转换或去除连字符。示例："SN20240315001"、"A1B2-C3D4"。

        Returns:
            该 SN 对应的售后维修工单数量（整数）。无记录时返回 0。
        """
        return (await _fetch(sn)).get("count", 0)

    @mcp.tool()
    async def search_sn_in_sales_post_order_data(sn: str) -> list:
        """查询某台机器在 CRM 系统中的详细信息。

        适用场景：用户输入了一个sn号或者想了解"某个机器的相关信息"、"某台机器的详细信息"等需要看具体内容的问题。
        如果只是想知道维修次数，请改用 search_sn_in_sales_post_order_count。

        Args:
            sn: 机器序列号（Serial Number），厂商出厂的唯一编号。直接传入
                用户提供的原始字符串，不要做大小写转换或去除连字符。
                示例："SN20240315001"、"A1B2-C3D4"。

        Returns:
            包含一条机器全部信息字段的列表，典型字段含工单号、报修日期、故障
            描述、维修状态、客户信息等。无记录时返回空列表 []。
        """
        return (await _fetch(sn)).get("data", [])

    @mcp.tool()
    async def get_repair_process_status_by_sn(sn: str) -> dict:
        """根据 SN 号查询某台机器在MES系统中的当前工序（维修状态）和最近更新时间。

        适用场景：用户输入了sn号或者想知道"这台机器现在的维修状态"、"当前在什么工序"、
        等关于**实时状态**的问题。返回的是机器在MES系统中的当前工序（如"装箱"、
        "上料"、"质检"等）。

        与售后查询的区别：
        - 本工具：MES系统中实时的当前工序
        - search_sn_in_sales_post_order_count / _data：CRM 系统中的机器详细信息

        Args:
            sn: 机器序列号（Serial Number），厂商出厂的唯一编号。直接传入
                用户提供的原始字符串，不要做大小写转换或去除连字符。
                示例："MC705"、"SN20240315001"。

        Returns:
            字典，包含字段：
            - Sn (str): 机器序列号，回显输入。
            - CurrentProcess (str): 当前流程节点名称，如"装箱"。
            - UpdateDate (str): 最近一次状态更新时间，ISO 8601 格式带时区，
              如 "2022-03-15T09:24:41+08:00"。
            若该 SN 不存在或无记录，返回空字典 {}。
        """
        return await _fetch_repair_process(sn)
