import os

from dotenv import load_dotenv

load_dotenv()


HOST = os.getenv("MCP_HOST", "")
PORT = int(os.getenv("MCP_PORT", "8765"))

SEARCH_SN_IN_SALES_POST_ORDER_URL = os.getenv(
    "SEARCH_SN_IN_SALES_POST_ORDER_URL",
    "https://e.com/api/c/c044/SearchSNInSalesPostOrder",
)

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "")
LOGIN_USERNAME = os.getenv("LOGIN_USERNAME", "")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
LOGIN_URL = os.getenv("LOGIN_URL", "https://as/pi/s/m/login")
GETSN_URL = os.getenv("GETSN_URL", "https://ti/open/m/m/m/GetSn")
GET_DEVICE_PROFILE_URL = os.getenv("GET_DEVICE_PROFILE_URL", "https://placeholder/GetDeviceProfile")
GET_FQC_REPORT_URL = os.getenv("GET_FQC_REPORT_URL", "https://placeholder/GetFqcReport")

# FQC 报告解码后落地保存的目录
FQC_REPORT_DIR = os.getenv("FQC_REPORT_DIR", os.path.expanduser("~/fqc_reports"))
