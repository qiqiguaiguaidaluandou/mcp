# mcpserver

一个基于 [Model Context Protocol](https://modelcontextprotocol.io/) 的个人 MCP 服务，把企业内部 CRM、生产/维修等接口包装成大模型可直接调用的工具，对接 Claude Code、Claude Desktop、Cursor 等 MCP 客户端。

通过 Streamable HTTP 传输暴露统一 endpoint，支持 CORS，可被多个客户端同时接入。

## 功能

当前已注册的工具（位于 `src/mcpserver/tools/sales_order.py`）：

| 工具名 | 用途 | 鉴权方式 |
|---|---|---|
| `search_sn_in_sales_post_order_count` | 统计某 SN 在 CRM 的售后维修工单总数 | 无鉴权 |
| `search_sn_in_sales_post_order_data` | 查询某 SN 最近一次售后维修工单详情 | 无鉴权 |
| `get_repair_process_status_by_sn` | 查询某 SN 在生产/维修流水线的当前流程节点 | JWT + 票据，自动缓存与续期 |

`get_repair_process_status_by_sn` 内部完成三步流程：

1. 用 `JWT_SECRET` / `JWT_ISSUER` 本地生成 HS256 JWT（60 分钟有效期）
2. 用 JWT 调登录接口换取 `Ticket` 和 `InvOrgId`
3. 用 `Ticket` 调 GetSN 接口获取实时流程状态

JWT 与 Ticket 共享缓存，55 分钟 TTL（提前 5 分钟刷新作为时钟偏差余量），`asyncio.Lock` 保证并发首次未命中时只发起一次登录。

## 项目结构

```
mcpserver/
├── pyproject.toml              # 项目元数据 + 依赖 + 入口脚本
├── .env.example                # 环境变量模板
├── DESIGN.md                   # 设计文档
├── 需求文档.md                  # 业务需求
└── src/mcpserver/
    ├── __init__.py
    ├── server.py               # 入口：装配 FastMCP + CORS + uvicorn
    ├── config.py               # 环境变量统一读取（自动加载 .env）
    └── tools/
        ├── __init__.py
        └── sales_order.py      # 售后查询 + 维修流程查询工具
```

设计原则：

- `server.py` 只负责装配，不写业务逻辑
- `config.py` 所有可变量从环境变量读，禁止硬编码
- 一个文件一个主题域，对外只暴露 `register(mcp)` 函数

## 环境要求

- Python ≥ 3.10
- 网络可达：所配置的 CRM、登录、GetSN 接口

## 快速开始

### 1. 克隆并进入项目

```bash
cd /root/kqspace/mcpserver
```

### 2. 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

`-e .` 是开发模式安装，源码改动立即生效。

### 3. 配置 `.env`

```bash
cp .env.example .env
```

然后编辑 `.env`，填入真实值：

```ini
MCP_HOST=127.0.0.1
MCP_PORT=8765

SEARCH_SN_IN_SALES_POST_ORDER_URL=https://your.crm/api/SearchSNInSalesPostOrder

JWT_SECRET=                         # JWT 签名用的账号
JWT_ISSUER=                         # JWT 的 iss 字段
LOGIN_USERNAME=                     # login 接口 Parameters[0].Value
LOGIN_PASSWORD=                     # login 接口 Parameters[1].Value
LOGIN_URL=https://.../login
GETSN_URL=https://.../GetSn
```

> **注意**：`.env` 里的值不要加引号；`.gitignore` 已包含 `.env`，不会被提交。

### 4. 启动服务

```bash
mcpserver
```

或等价的：

```bash
python3 -m mcpserver.server
```

启动成功会看到：

```
INFO:     Uvicorn running on http://127.0.0.1:8765
INFO:     Application startup complete.
```

MCP endpoint 为 `http://<MCP_HOST>:<MCP_PORT>/mcp`。

### 5. 验证服务

```bash
curl -i http://127.0.0.1:8765/mcp
```

只要不是连接拒绝就说明端口已监听（MCP 协议本身需要客户端握手才能看到 tool 列表）。

## 客户端接入

### Claude Code

```bash
claude mcp add --transport http mcpserver http://127.0.0.1:8765/mcp
```

之后在 Claude Code 中通过 `/mcp` 查看已连接的服务和工具。

### Claude Desktop / Cursor

在客户端的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "mcpserver": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

### MCP Inspector（调试用）

```bash
npx @modelcontextprotocol/inspector
```

选 Streamable HTTP 传输并填入同一 URL，可视化调用每个工具。

## 配置项

所有变量都可在 `.env` 中配置，也可通过 shell `export` 覆盖（shell 优先级更高）。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MCP_HOST` | *(空，需填)* | 服务监听地址，本机调试用 `127.0.0.1`，对外用 `0.0.0.0` |
| `MCP_PORT` | `8765` | 服务监听端口 |
| `SEARCH_SN_IN_SALES_POST_ORDER_URL` | `https://e.com/api/c/c044/SearchSNInSalesPostOrder` | 售后工单查询接口地址 |
| `JWT_SECRET` | *(空)* | JWT HS256 签名密钥（业务侧账号） |
| `JWT_ISSUER` | *(空)* | JWT `iss` 字段 |
| `LOGIN_USERNAME` | *(空)* | login 接口请求体 `Parameters[0].Value` |
| `LOGIN_PASSWORD` | *(空)* | login 接口请求体 `Parameters[1].Value` |
| `LOGIN_URL` | *(空)* | 登录接口完整 URL |
| `GETSN_URL` | *(空)* | GetSN 接口完整 URL |

## 扩展：新增工具

1. 在 `src/mcpserver/tools/` 下新建 `<topic>.py`：

   ```python
   def register(mcp):
       @mcp.tool()
       async def do_something(arg: str) -> dict:
           """一句话说明工具用途。

           适用场景：...
           Args:
               arg: ...
           Returns:
               ...
           """
           ...
   ```

2. 在 `server.py` 中导入并注册：

   ```python
   from mcpserver.tools import sales_order, your_new_tool

   sales_order.register(mcp)
   your_new_tool.register(mcp)
   ```

3. 重启服务即可。

**写好工具描述很关键** —— 大模型是根据 docstring + 参数签名 + 类型注解判断调用哪个工具的。建议每个工具都明确写出：适用场景、与同类工具的区别、参数格式示例、返回值结构。

## 常见问题

**`ModuleNotFoundError: No module named 'jwt'` 或 `'dotenv'`**
依赖没装好，重跑 `pip install -e .`。

**启动报地址相关错误**
`MCP_HOST` 在 `.env` 里没填值。

**Login 返回 `401 Unauthorized`**
JWT 被服务端拒绝。逐项排查：
- `.env` 里 `JWT_SECRET` / `JWT_ISSUER` 是否填错（注意不要加引号、空格、换行）
- 把生成的 token 拿去 [jwt.io](https://jwt.io) 验证签名是否正确
- 平台是否要求自定义 header（不是 `Authorization: Bearer ...`）
- 系统时间是否准（`date -u`），偏差过大会被 `nbf` 拒绝

**改了 `.env` 后没生效**
`.env` 是进程启动时一次性读的，改完必须重启服务。

**Pylance 提示工具函数 "未存取"**
误报。`@mcp.tool()` 装饰器在框架内部注册函数，本文件不会显式调用。可忽略。

## 安全建议

| 场景 | 建议 |
|---|---|
| 本地单机 | 保持 `MCP_HOST=127.0.0.1`，避免误暴露到局域网 |
| 公网部署 | 前置 nginx/Caddy 启用 HTTPS，并在 endpoint 前加鉴权或 IP 白名单 |
| 凭据管理 | `JWT_SECRET` / `LOGIN_PASSWORD` 等只放 `.env` 或环境变量，禁止写入代码或日志 |
| 超时 | 所有 `httpx` 调用均设 15s 超时，避免 tool 调用挂起 |

## 相关文档

- [DESIGN.md](./DESIGN.md) — 架构与方案设计
- [需求文档.md](./需求文档.md) — `get_repair_process_status_by_sn` 的接口规范
