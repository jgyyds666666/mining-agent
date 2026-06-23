# ⛏️ 矿权日报 Agent — Mining Daily Agent

基于 **MCP (Model Context Protocol)** 和 **LangGraph** 的智能矿业数据聚合与报告生成系统。输入一个查询，自动输出 Markdown 格式的矿业日报。

```bash
# 一条命令，一份完整日报
docker compose run --rm agent "给我生成一份关于 Pilbara 锂矿的今日简报"
```

---

## 架构总览

```
  用户查询 ──▶  ┌────────────────────────────────────────────────┐
                │            LangGraph Agent                     │
                │  parse_intent → gather_data → synthesize_report │
                └──────────┬──────────┬──────────┬──────────────┘
                           │          │          │
                     ┌─────┘     ┌────┘     ┌──┘
                     ▼           ▼          ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ mining-  │ │ mineral- │ │ lme-     │
              │ news-mcp │ │ pdf-mcp  │ │ price-mcp│
              │ :8001    │ │ :8002    │ │ :8003    │
              └──────────┘ └──────────┘ └──────────┘
                     │           │           │
                     ▼           ▼           ▼
               📰 新闻数据   📊 储量数据   📈 价格数据
```

### 组件说明

| 组件 | 协议 | 端口 | 工具 | 职责 |
|------|------|------|------|------|
| **mining-news-mcp** | SSE | 8001 | `search()` `fetch_article()` | 矿业新闻关键词搜索与全文获取 |
| **mineral-pdf-mcp** | SSE | 8002 | `extract_resources()` | NI 43-101 资源量报告解析 (Indicated/Inferred) |
| **lme-price-mcp** | SSE | 8003 | `get_price()` `get_trend()` | LME 大宗商品实时价格与 30 日走势 |
| **Agent (LangGraph)** | — | — | `StateGraph` | 意图解析 → 并行数据采集 → 报告合成 |

---

## 快速启动

### 方式一：Docker（推荐）

```bash
# 1. 构建并启动所有服务
docker compose up -d --build

# 2. 生成日报（替换为你自己的查询）
docker compose run --rm agent "给我生成一份关于 Pilbara 锂矿的今日简报"

# 可选：设置 DeepSeek API Key 开启 LLM 智能分析
export DEEPSEEK_API_KEY=sk-your-key-here
docker compose run --rm agent "给我生成一份关于 Pilbara 锂矿的今日简报"
```

> 🐳 Docker Hub 在国内部分地区可能无法访问，请自配镜像源或用方式二。

### 方式二：本地 Conda 环境

```bash
# 1. 创建并激活环境
conda create -n mining-agent python=3.11 -y
conda activate mining-agent

# 2. 安装依赖
pip install mcp>=1.28.0 openai>=1.0.0 langgraph>=0.3.0

# 3. 一键启动（自动启动 3 个 MCP Server + 运行 Agent）
python run_local.py "给我生成一份关于 Pilbara 锂矿的今日简报"

# 也可以先启动服务，再查询
python run_local.py  # 会进入交互模式
```

### 方式三：Claude Desktop / Cursor

1. 先启动 3 个 MCP Server：
   ```bash
   docker compose up -d mining-news-mcp mineral-pdf-mcp lme-price-mcp
   ```
2. 在 Claude Desktop 或 Cursor 中导入 [`mcp-config.json`](./mcp-config.json)，即可直接调用工具。

---

## 使用示例

```bash
# Pilbara 锂矿日报
docker compose run --rm agent "给我生成一份关于 Pilbara 锂矿的今日简报"

# 自定义公司
docker compose run --rm agent "分析一下 Pilbara Minerals 的近期动态"

# 查看锂价
docker compose run --rm agent "锂价最近走势如何"

# 英文查询
docker compose run --rm agent "Generate a daily report for Pilbara Minerals"
```

---

## 输出预览

运行后会生成如下结构的 Markdown 报告：

```markdown
# 📋 矿权日报 — Pilbara Minerals

**生成日期**: 2026-06-23

---

## 📰 新闻摘要

**1. Pilbara Minerals 发布 FY2026 产量指引**
   - 公司预计 FY2026 锂精矿产量 85-90 万吨...
   — MiningNews.net | 2026-06-20 | [原文链接](https://...)

**2. Pilbara 与赣锋锂业续签包销协议**
   - ...

---

## 📊 储量数据 (NI 43-101)

**公司**: Pilbara Minerals Ltd
**项目**: Pilgangoora Lithium-Tantalum Project
| 类别 | 吨位 (t) | 品位 (% Li₂O) | 含金属量 (t LCE) |
|------|----------|---------------|------------------|
| Indicated | 214,000,000 | 1.52% | 1,520,000 |
| Inferred | 106,000,000 | 1.31% | 680,000 |
| **Total** | **320,000,000** | — | **2,200,000** |

---

## 📈 价格走势

**当前价格**: 8,660 USD/t LCE
**30 日走势统计**:
- 最高: 8,920 USD/t | 最低: 8,600 USD/t
- 均值: 8,750 USD/t | 涨跌: -1.69%

---

## ⚠️ 风险提示

- ⚠️ **锂价持续承压**: 30 日内锂价下跌 1.7%...
- ⚠️ **运营成本上升**: 西澳矿业劳动力成本上升...
- ⚠️ **下游需求不确定性**: 全球电动汽车增速放缓...
```

---

## 项目结构

```
mining-daily-agent/
├── docker-compose.yml              # Docker Compose 编排
├── mcp-config.json                  # Claude Desktop / Cursor MCP 配置
├── run_local.py                     # 本地一键启动脚本
├── README.md                        # 本文件
├── .gitignore
├── servers/                         # 3 个 MCP Server
│   ├── mining-news-mcp/             # 📰 矿业新闻（端口 8001）
│   │   ├── server.py                #   search() + fetch_article()
│   │   ├── data/news_samples.json   #   新闻样本数据
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── mineral-pdf-mcp/             # 📊 储量解析（端口 8002）
│   │   ├── server.py                #   extract_resources()
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── lme-price-mcp/               # 📈 价格行情（端口 8003）
│       ├── server.py                #   get_price() + get_trend()
│       ├── data/lme_prices.json     #   30 日价格数据
│       ├── Dockerfile
│       └── requirements.txt
└── agent/                           # LangGraph Agent 编排
    ├── main.py                      #   入口（CLI / 交互模式）
    ├── graph.py                     #   LangGraph StateGraph 编排
    ├── mcp_client.py                #   MCP SSE 客户端封装
    ├── prompts.py                   #   提示词 + 模板 + 数据格式化
    ├── Dockerfile
    └── requirements.txt
```

---

## 环境变量

| 变量 | 必须 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | 推荐 | — | DeepSeek API 密钥，开启 LLM 智能解析与生成 |
| `DEEPSEEK_BASE_URL` | 可选 | `https://api.deepseek.com` | DeepSeek API 地址（自部署时修改） |
| `MCP_HOST` | 可选 | `localhost` | `remote` 时使用 Docker 服务名寻址 |

> 💡 **没有 API Key 也能用**：自动降级为模板模式，输出结构一致的 Markdown 报告。

---

## 工作原理

1. **parse_intent** — 用 DeepSeek LLM 从查询中提取公司和商品名，失败时使用关键词启发式回退
2. **gather_data** — `asyncio.gather` 并发调用 3 个 MCP Server，获取新闻、价格、储量数据
3. **synthesize_report** — 将结构化数据输入 DeepSeek 生成自然语言日报，失败时用 Jinja2 模板生成保底报告

---

## 数据说明

当前包含 **模拟示例数据**，便于快速体验完整流程：

- **新闻**: 5 篇 Pilbara Minerals 相关中文新闻（产量指引、包销协议、资源量更新等）
- **储量**: Pilgangoora 项目 NI 43-101 模拟数据（Indicated 214Mt @ 1.52% Li₂O）
- **价格**: 30 天锂价走势模拟数据（8,660–8,920 USD/t LCE）

替换 `data/` 目录下的 JSON 文件即可接入真实数据源。

---

## 技术栈

| 技术 | 用途 |
|------|------|
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) ≥1.28.0 | MCP 协议实现（FastMCP + SSEClient） |
| [LangGraph](https://github.com/langchain-ai/langgraph) ≥0.3.0 | Agent 状态图编排 |
| [DeepSeek API](https://platform.deepseek.com/) | LLM 意图解析 + 报告生成 |
| Docker Compose | 容器编排 |
| Python 3.11 | 运行环境 |

---

## License

MIT
