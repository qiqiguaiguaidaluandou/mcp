"""FQC（出厂质检）报告查询工具（按 SN）。

请求体为简单的 {"sn": ...}，鉴权只需 JWT（token 直接放 Authorization 头），
与 CRM 售后查询一致，不需要票据。

接口返回的是 Base64 编码的报告文件（实际为 Excel）。本工具解码还原成原始文件
并保存到本地（config.FQC_REPORT_DIR），返回文件名与保存路径，可直接打开。
"""

import base64
import os

from mcpserver import auth, config


async def _fetch_fqc_report(sn: str) -> dict:
    data = await auth.post_with_jwt(config.GET_FQC_REPORT_URL, {"sn": sn})
    file_base64 = data.get("fileBase64")
    if not file_base64:
        return {}
    raw = base64.b64decode(file_base64)
    file_name = data.get("fileName") or f"{sn}.xlsx"

    os.makedirs(config.FQC_REPORT_DIR, exist_ok=True)
    # 用 sn 前缀，避免不同设备的同名报告互相覆盖
    saved_path = os.path.abspath(os.path.join(config.FQC_REPORT_DIR, f"{sn}_{file_name}"))
    with open(saved_path, "wb") as f:
        f.write(raw)

    return {"fileName": file_name, "savedPath": saved_path}


def register(mcp):
    @mcp.tool()
    async def get_fqc_report_by_sn(sn: str) -> dict:
        """根据 SN 号查询某台设备的 FQC（出厂质检）报告文件。

        适用场景：用户输入了 sn 号或者想"查看/下载这台设备的 FQC 报告"、
        "出厂质检报告"等问题。报告接口返回的是 Base64 编码的 Excel 文件，
        本工具会自动解码还原成原始文件并保存到本地，返回保存路径供打开查看。

        Args:
            sn: 机器序列号（Serial Number），厂商出厂的唯一编号。直接传入
                用户提供的原始字符串，不要做大小写转换或去除连字符。
                示例："MC0BCJD00302"、"SN20240315001"。

        Returns:
            字典，包含字段：
            - fileName (str): 报告原始文件名，如 "FQC.xlsx"。
            - savedPath (str): 报告已保存到的本地绝对路径，可直接打开。
            若该 SN 不存在或无报告，返回空字典 {}。
        """
        return await _fetch_fqc_report(sn)
