import os

HOST = os.getenv("MCP_HOST", "127.10.42.142")
PORT = int(os.getenv("MCP_PORT", "8765"))

MY_API_BASE_URL = os.getenv("MY_API_BASE_URL", "https://httpbin.org")
MY_API_TOKEN = os.getenv("MY_API_TOKEN", "")
