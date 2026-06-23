"""MCP SSE 客户端封装 — 调用 3 个 MCP Server 的工具"""

import json
import logging
import os
from typing import Any

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

logger = logging.getLogger(__name__)

# MCP 服务器地址
# 本地运行用 localhost，Docker 模式下通过 MCP_HOST=remote 使用 service 名
if os.environ.get("MCP_HOST") == "remote":
    MCP_SERVERS = {
        "mining-news": "http://mining-news-mcp:8001/sse",
        "mineral-pdf": "http://mineral-pdf-mcp:8002/sse",
        "lme-price": "http://lme-price-mcp:8003/sse",
    }
else:
    # 默认本地模式
    MCP_SERVERS = {
        "mining-news": "http://localhost:8001/sse",
        "mineral-pdf": "http://localhost:8002/sse",
        "lme-price": "http://localhost:8003/sse",
    }


def _extract_text(result: Any) -> str:
    """Extract text content from MCP CallToolResult."""
    if hasattr(result, "content") and result.content:
        for item in result.content:
            if hasattr(item, "text") and item.text:
                return item.text
            if isinstance(item, dict) and item.get("type") == "text":
                return item.get("text", "")
    # Fallback — try to stringify
    text = str(result)
    return text.replace("TextContent(", "").replace(")", "") if "text=" in text else text


async def call_tool(server_name: str, tool_name: str, args: dict) -> str:
    """Call an MCP tool on the specified server and return the JSON result string."""
    url = MCP_SERVERS.get(server_name)
    if not url:
        raise ValueError(f"Unknown MCP server: {server_name}. Available: {list(MCP_SERVERS.keys())}")

    logger.info("[mcp] %s.%s(%s)", server_name, tool_name, args)

    try:
        async with sse_client(url=url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                text = _extract_text(result)
                logger.debug("[mcp] %s.%s → %s…", server_name, tool_name, text[:120])
                return text
    except Exception as exc:
        logger.warning("[mcp] %s.%s failed: %s", server_name, tool_name, exc)
        raise


async def search_news(query: str, days: int = 7) -> list[dict]:
    """Search mining news."""
    raw = await call_tool("mining-news", "search", {"query": query, "days": days})
    return json.loads(raw)


async def fetch_article(url: str) -> dict:
    """Fetch full article content."""
    raw = await call_tool("mining-news", "fetch_article", {"url": url})
    return json.loads(raw)


async def get_resource(pdf_url: str) -> dict:
    """Extract NI 43-101 mineral resources."""
    raw = await call_tool("mineral-pdf", "extract_resources", {"pdf_url": pdf_url})
    return json.loads(raw)


async def get_price(commodity: str, date: str = "today") -> dict:
    """Get current price."""
    raw = await call_tool("lme-price", "get_price", {"commodity": commodity, "date": date})
    return json.loads(raw)


async def get_trend(commodity: str, days: int = 30) -> dict:
    """Get price trend."""
    raw = await call_tool("lme-price", "get_trend", {"commodity": commodity, "days": days})
    return json.loads(raw)
