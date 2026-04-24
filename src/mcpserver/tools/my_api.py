import httpx

from mcpserver.config import MY_API_BASE_URL, MY_API_TOKEN


def _headers() -> dict:
    return {"Authorization": f"Bearer {MY_API_TOKEN}"} if MY_API_TOKEN else {}


def register(mcp):
    @mcp.tool()
    async def my_api_get(path: str, params: dict | None = None) -> dict:
        """GET against your own API. Replace with domain-specific tools
        (e.g. `list_orders`, `create_ticket`) once endpoints are finalized.

        Args:
            path: path under MY_API_BASE_URL, e.g. "/get" or "/users/42".
            params: optional query params.
        """
        url = f"{MY_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params or {}, headers=_headers())
            r.raise_for_status()
            return r.json()

    @mcp.tool()
    async def my_api_post(path: str, body: dict | None = None) -> dict:
        """POST JSON to your own API."""
        url = f"{MY_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=body or {}, headers=_headers())
            r.raise_for_status()
            return r.json()
