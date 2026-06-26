"""FQC（出厂质检）报告查询工具（按 SN）。

请求体为简单的 {"sn": ...}，鉴权只需 JWT（token 直接放 Authorization 头），
与 CRM 售后查询一致，不需要票据。
"""

from mcpserver import auth, config


async def _fetch_fqc_report(sn: str) -> dict:
    return await auth.post_with_jwt(config.GET_FQC_REPORT_URL, {"sn": sn})


def register(mcp):
    @mcp.tool()
    async def get_fqc_report_by_sn(sn: str) -> dict:
        """根据 SN 号查询某台设备的 FQC（出厂质检）报告文件。

        适用场景：用户输入了 sn 号或者想"查看/下载这台设备的 FQC 报告"、
        "出厂质检报告"、"质检文件"等问题。返回的是报告文件本身（文件名 +
        Base64 编码的文件内容）。

        Args:
            sn: 机器序列号（Serial Number），厂商出厂的唯一编号。直接传入
                用户提供的原始字符串，不要做大小写转换或去除连字符。
                示例："MC0BCJD00302"、"SN20240315001"。

        Returns:
            字典，包含字段：
            - fileName (str): 报告文件名，如 "FQC.txt"。
            - fileBase64 (str): 报告文件内容的 Base64 编码字符串，需解码后
              才能得到原始文件。
            若该 SN 不存在或无报告，返回空字典 {}。
        """
        return await _fetch_fqc_report(sn)
