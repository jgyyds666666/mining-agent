# 矿权日报 Agent — 5 分钟快速启动

## 前置条件

| 工具 | 版本要求 | 验证命令 |
|------|---------|---------|
| Docker Desktop | v24+ | `docker compose version` |
| Git | 任意 | `git version` |

## 快速启动

### 1. 启动 3 个 MCP Server（后台运行）

```bash
# 在当前目录下
cd mining-daily-agent

# 构建并启动所有服务
docker compose up -d --build mining-news-mcp mineral-pdf-mcp lme-price-mcp

# 确认服务运行中
docker compose ps
# 应看到 3 个服务状态为 "Up"
```

### 2. 一键生成报告（推荐）

```bash
# 设置 DeepSeek API Key（可选，不设置则使用模板模式）
export DEEPSEEK_API_KEY=sk-your-key-here

# 运行 Agent 生成报告
docker compose run --rm agent "给我生成一份关于 Pilbara 锂矿的今日简报"
```

### 3. 交互模式

```bash
# 启动所有服务
docker compose up -d --build

# 进入 Agent 交互模式
docker compose run --rm agent
# 然后输入查询
```

### 4. 全部一键启动（含日志）

```bash
docker compose up --build
# 然后打开另一个终端，用 docker compose run agent "查询"
```

## 示例查询

```bash
# Pilbara 锂矿
docker compose run --rm agent "给我生成一份关于 Pilbara 锂矿的今日简报"

# 自定义公司
docker compose run --rm agent "分析一下 Pilbara Minerals 的近期动态"

# 查看价格
docker compose run --rm agent "锂价最近走势如何"

# 英文查询
docker compose run --rm agent "Generate a daily report for Pilbara Minerals"
```

## 使用 Claude Desktop / Cursor

1. 先启动 3 个 MCP Server：
   ```bash
   docker compose up -d --build mining-news-mcp mineral-pdf-mcp lme-price-mcp
   ```

2. 在 Claude Desktop 或 Cursor 的 MCP 配置中导入 `mcp-config.json`：
   - Claude Desktop: Settings → MCP → Import Config
   - Cursor: Settings → Features → MCP → Add

3. 配置导入后，Claude 即可直接调用 3 个 MCP Server 的工具。

## 环境变量

| 变量 | 必须 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | 推荐 | — | DeepSeek API 密钥，用于智能解析和生成 |
| `DEEPSEEK_BASE_URL` | 可选 | `https://api.deepseek.com` | DeepSeek API 地址（自部署时修改） |

> 💡 **没有 API Key 也能用**：Agent 会自动降级为模板模式，报告结构一致，但缺少 LLM 的智能分析能力。

## 项目结构

```
mining-daily-agent/
├── docker-compose.yml          # 一键编排
├── mcp-config.json             # Claude Desktop/Cursor 配置
├── RUN.md                      # 本文件
├── servers/
│   ├── mining-news-mcp/        # 矿业新闻聚合
│   │   ├── server.py           #   search() + fetch_article()
│   │   └── data/news_samples.json
│   ├── mineral-pdf-mcp/        # NI 43-101 储量解析
│   │   └── server.py           #   extract_resources()
│   └── lme-price-mcp/          # 价格行情
│       ├── server.py           #   get_price() + get_trend()
│       └── data/lme_prices.json
└── agent/                      # LangGraph Agent
    ├── main.py                 #   入口
    ├── graph.py                #   LangGraph 编排
    ├── mcp_client.py           #   MCP SSE 客户端
    └── prompts.py              #   提示词 + 模板
```

## 输出示例

运行后会在终端输出 Markdown 格式的简报，包含：
- 📋 标题 + 日期
- 📰 新闻摘要（含来源链接）
- 📊 NI 43-101 储量数据表格
- 📈 LME 价格走势
- ⚠️ 风险提示

## 故障排查

| 问题 | 解决 |
|------|------|
| `Connection refused` | MCP Server 未启动，检查 `docker compose ps` |
| Agent 报错 `No such host` | docker network 问题，重启 docker：`docker compose down && docker compose up -d` |
| DeepSeek API 超时 | 检查网络和 `DEEPSEEK_API_KEY` 是否正确 |
| 端口被占用 | 修改 `docker-compose.yml` 中的 `ports` 映射 |
