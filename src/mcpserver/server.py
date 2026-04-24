import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from mcpserver.config import HOST, PORT
from mcpserver.tools import my_api, sales_order, weather

mcp = FastMCP("mcpserver", host=HOST, port=PORT)

weather.register(mcp)
# my_api.register(mcp)
sales_order.register(mcp)


def main() -> None:
    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
