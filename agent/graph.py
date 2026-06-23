"""LangGraph 定义 — 矿权日报 Agent 编排"""

import json
import logging
import os
from datetime import datetime
from typing import Annotated, List, Optional, TypedDict

from openai import AsyncOpenAI

from langgraph.graph import END, START, StateGraph

from mcp_client import get_price, get_resource, get_trend, search_news
from prompts import (
    PARSE_INTENT_SYSTEM,
    SYNTHESIS_SYSTEM,
    TEMPLATE_REPORT,
    build_news_section,
    build_price_section,
    build_resource_section,
    build_risk_section,
)

logger = logging.getLogger(__name__)

# ── DeepSeek 客户端 ──
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
_llm = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL) if DEEPSEEK_API_KEY else None


# ── 状态定义 ──

class MiningState(TypedDict):
    query: str
    company: str
    commodity: str
    news: List[dict]
    price_current: Optional[dict]
    price_trend: Optional[dict]
    resources: Optional[dict]
    report: str
    errors: Annotated[List[str], lambda a, b: a + b]


def _init_state(query: str) -> MiningState:
    return {
        "query": query,
        "company": "",
        "commodity": "",
        "news": [],
        "price_current": None,
        "price_trend": None,
        "resources": None,
        "report": "",
        "errors": [],
    }


# ── LLM 调用辅助 ──

async def _call_llm(system: str, user: str, default: str = "") -> str:
    """调用 DeepSeek API，失败时返回 default"""
    if _llm is None:
        return default
    try:
        resp = await _llm.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return resp.choices[0].message.content or default
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return default


# ── 节点 1: 解析意图 ──

async def parse_intent(state: MiningState) -> dict:
    query = state["query"]

    # 先尝试 LLM
    if _llm:
        raw = await _call_llm(PARSE_INTENT_SYSTEM, query)
        if raw:
            try:
                parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
                company = parsed.get("company", "")
                commodity = parsed.get("commodity", "lithium")
                logger.info("parse_intent: company=%s commodity=%s", company, commodity)
                return {"company": company, "commodity": commodity}
            except (json.JSONDecodeError, AttributeError):
                pass

    # 关键词启发式回退
    query_lower = query.lower()
    company = "Pilbara Minerals" if any(k in query_lower for k in ["pilbara", "pilgangoora", "pls"]) else query
    commodity = "lithium" if any(k in query_lower for k in ["锂", "lithium", "lce", "spodumene"]) else "lithium"
    logger.info("parse_intent (fallback): company=%s commodity=%s", company, commodity)
    return {"company": company, "commodity": commodity}


# ── 节点 2: 并行获取数据 ──

async def gather_data(state: MiningState) -> dict:
    company = state["company"]
    commodity = state["commodity"]
    errors: list[str] = []

    # 用 company 加 commodity 作为新闻搜索关键词
    search_query = f"{company} {commodity}"
    pdf_lookup = company.lower().replace(" ", "_") + "_43-101"

    # 并行调用所有 MCP
    import asyncio

    tasks = {
        "news": search_news(search_query, 7),
        "price": get_price(commodity, "today"),
        "trend": get_trend(commodity, 30),
        "resources": get_resource(pdf_lookup),
    }

    # 用 asyncio.gather 并发执行
    results = await asyncio.gather(
        *tasks.values(), return_exceptions=True
    )

    updates: dict = {}
    keys = list(tasks.keys())

    for key, result in zip(keys, results):
        if isinstance(result, Exception):
            logger.warning("gather_data: %s failed: %s", key, result)
            errors.append(f"{key}: {result}")
            updates[key] = [] if key == "news" else None
        elif key == "news":
            updates["news"] = result if isinstance(result, list) else []
        elif key == "price":
            updates["price_current"] = result if isinstance(result, dict) else None
        elif key == "trend":
            updates["price_trend"] = result if isinstance(result, dict) else None
        elif key == "resources":
            updates["resources"] = result if isinstance(result, dict) else None

    updates["errors"] = errors
    logger.info("gather_data: news=%d price=%s resources=%s errors=%d",
                len(updates.get("news", [])),
                "ok" if updates.get("price_current") else "fail",
                "ok" if updates.get("resources") else "fail",
                len(errors))
    return updates


# ── 节点 3: 合成简报 ──

async def synthesize_report(state: MiningState) -> dict:
    company = state["company"] or "矿业公司"
    commodity = state["commodity"] or "锂"
    news = state.get("news", [])
    price_current = state.get("price_current")
    price_trend = state.get("price_trend")
    resources = state.get("resources")
    errors = state.get("errors", [])

    # 尝试 DeepSeek 生成
    if _llm:
        # 构造结构化输入
        data_input = f"""公司: {company}
商品: {commodity}
日期: {datetime.now().strftime("%Y-%m-%d")}

新闻 ({len(news)} 条):
{json.dumps(news, ensure_ascii=False, indent=2)}

当前价格:
{json.dumps(price_current, ensure_ascii=False, indent=2) if price_current else "无数据"}

30日走势:
{json.dumps(price_trend, ensure_ascii=False, indent=2)[:500] if price_trend else "无数据"}

储量数据:
{json.dumps(resources, ensure_ascii=False, indent=2) if resources else "无数据"}

数据获取告警: {"; ".join(errors) if errors else "无"}
"""
        report = await _call_llm(SYNTHESIS_SYSTEM, data_input)
        if report:
            logger.info("synthesize_report: LLM 生成成功 (%d chars)", len(report))
            return {"report": report}

    # 模板回退
    logger.info("synthesize_report: 使用模板模式")
    date_str = datetime.now().strftime("%Y-%m-%d")
    report = TEMPLATE_REPORT.format(
        company=company,
        date=date_str,
        news_section=build_news_section(news),
        resource_section=build_resource_section(resources),
        price_section=build_price_section(price_current, price_trend),
        risk_section=build_risk_section(news, price_trend),
    )
    return {"report": report}


# ── 构建 LangGraph ──

def build_graph() -> StateGraph:
    graph = StateGraph(MiningState)

    graph.add_node("parse_intent", parse_intent)
    graph.add_node("gather_data", gather_data)
    graph.add_node("synthesize_report", synthesize_report)

    graph.add_edge(START, "parse_intent")
    graph.add_edge("parse_intent", "gather_data")
    graph.add_edge("gather_data", "synthesize_report")
    graph.add_edge("synthesize_report", END)

    return graph.compile()


async def run_agent(query: str) -> str:
    """入口：运行完整的 agent 流程，返回 Markdown 报告"""
    graph = build_graph()
    state = _init_state(query)
    final = await graph.ainvoke(state)
    return final.get("report", "生成报告失败")
