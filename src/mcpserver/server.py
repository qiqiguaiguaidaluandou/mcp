from mcp.server.fastmcp import FastMCP

from mcpserver.config import HOST, PORT
from mcpserver.tools import my_api, weather

mcp = FastMCP("mcpserver", host=HOST, port=PORT)

weather.register(mcp)
my_api.register(mcp)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
