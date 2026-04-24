import httpx

ENDPOINT = "https://e.com/api/c/c044/SearchSNInSalesPostOrder"


def register(mcp):
    @mcp.tool()
    async def search_sn_in_sales_post_order(sn: str) -> dict:
        """根据 SN 号在销售发货单中查询对应记录。

        Args:
            sn: 设备序列号。
        """
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(ENDPOINT, json={"sn": sn})
            r.raise_for_status()
            return r.json()
