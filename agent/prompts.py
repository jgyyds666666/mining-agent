"""LLM 提示词和备用模板"""

# ── 解析意图：从用户查询中提取公司和商品 ──

PARSE_INTENT_SYSTEM = """你是一个矿业分析助手。从用户的查询中提取：
1. company: 公司名称（如 "Pilbara Minerals"）
2. commodity: 商品名称（如 "lithium" "锂"）

输出 JSON 格式：
{"company": "...", "commodity": "..."}

如果无法识别，使用默认值 {"company": "unknown", "commodity": "lithium"}。
只输出 JSON，不要多余文字。"""


# ── 生成简报 ──

SYNTHESIS_SYSTEM = """你是一个专业的矿业分析师。根据提供的结构化数据，生成一份中文"矿权日报"简报。

要求：
1. 语言：专业、简洁的中文
2. 结构：
   - 📋 标题 — 公司名称 + 日期
   - 📰 新闻摘要 — 每条新闻 1-2 句概括，**新闻标题需加粗**，末尾附新闻来源和原文链接
   - 📊 储量数据 — NI 43-101 Indicated / Inferred 储量表格
   - 📈 价格走势 — 当前价格 + 30 天趋势（高/低/均值/变化率）
   - ⚠️ 风险提示 — 至少 2 条，基于新闻和价格数据推断
3. 每条新闻末尾用 [来源](url) 格式标注来源链接
4. 如果有数据获取失败，在对应章节说明"数据暂缺"
5. 如果某些数据不存在（如公司信息为 unknown），合理推断"""


# ── 模板模式（无 DeepSeek API Key 时的回退） ──

TEMPLATE_REPORT = """# 📋 矿权日报 — {company}

**生成日期**: {date}

---

## 📰 新闻摘要

{news_section}

---

## 📊 储量数据 (NI 43-101)

{resource_section}

---

## 📈 价格走势

{price_section}

---

## ⚠️ 风险提示

{risk_section}

---

*报告由 Mining Daily Agent 自动生成 | 数据来源: 各 MCP Server*
"""


def build_news_section(news: list[dict]) -> str:
    if not news or (isinstance(news, list) and len(news) == 0):
        return "暂无相关新闻。\n"
    lines = []
    for i, article in enumerate(news, 1):
        title = article.get("title", "Untitled")
        source = article.get("source", "Unknown")
        summary = article.get("summary", "无摘要")
        url = article.get("url", "#")
        date = article.get("date", "")
        lines.append(f"**{i}. {title}**")
        lines.append(f"   - {summary}")
        lines.append(f"   — {source} | {date} | [原文链接]({url})")
        lines.append("")
    return "\n".join(lines)


def build_resource_section(resources: dict | None) -> str:
    if not resources or "error" in resources:
        return "暂无储量数据。\n"
    lines = []
    lines.append(f"**公司**: {resources.get('company', 'N/A')}")
    lines.append(f"**项目**: {resources.get('project', 'N/A')}")
    lines.append(f"**标准**: {resources.get('report_standard', 'N/A')} | **日期**: {resources.get('report_date', 'N/A')}")
    lines.append("")

    ind = resources.get("indicated", {})
    inf = resources.get("inferred", {})

    lines.append("| 类别 | 吨位 (t) | 品位 (% Li₂O) | 含金属量 (t LCE) |")
    lines.append("|------|----------|---------------|------------------|")
    ind_tons = f"{ind.get('tons', 0):,}" if isinstance(ind.get('tons'), (int, float)) else str(ind.get('tons', 'N/A'))
    ind_grade = f"{ind.get('grade_percent', 'N/A')}"
    ind_metal = f"{ind.get('contained_metal_lce', 0):,}" if isinstance(ind.get('contained_metal_lce'), (int, float)) else str(ind.get('contained_metal_lce', 'N/A'))
    lines.append(f"| Indicated | {ind_tons} | {ind_grade}% | {ind_metal} |")

    inf_tons = f"{inf.get('tons', 0):,}" if isinstance(inf.get('tons'), (int, float)) else str(inf.get('tons', 'N/A'))
    inf_grade = f"{inf.get('grade_percent', 'N/A')}"
    inf_metal = f"{inf.get('contained_metal_lce', 0):,}" if isinstance(inf.get('contained_metal_lce'), (int, float)) else str(inf.get('contained_metal_lce', 'N/A'))
    lines.append(f"| Inferred | {inf_tons} | {inf_grade}% | {inf_metal} |")

    total = resources.get("total", {})
    total_tons = f"{total.get('tons', 0):,}" if isinstance(total.get('tons'), (int, float)) else str(total.get('tons', 'N/A'))
    total_lce = f"{total.get('contained_metal_lce', 0):,}" if isinstance(total.get('contained_metal_lce'), (int, float)) else str(total.get('contained_metal_lce', 'N/A'))
    lines.append(f"| **Total** | **{total_tons}** | — | **{total_lce}** |")

    if resources.get("cutoff_grade"):
        lines.append(f"\n*截止品位: {resources['cutoff_grade']}*")
    if resources.get("mineralization_type"):
        lines.append(f"*矿化类型: {resources['mineralization_type']}*")

    return "\n".join(lines)


def build_price_section(price_current: dict | None, price_trend: dict | None) -> str:
    lines = []
    if price_current and "error" not in price_current:
        lines.append(f"**当前价格**: {price_current.get('price', 'N/A')} {price_current.get('unit', 'USD/t')}")
        lines.append(f"**日期**: {price_current.get('date', 'N/A')}")
        lines.append("")
    else:
        lines.append("当前价格: 数据暂缺\n")

    if price_trend and "error" not in price_trend:
        stats = price_trend.get("statistics", {})
        if stats:
            lines.append("**30 日走势统计**:")
            lines.append(f"- 最高: {stats.get('high', 'N/A')} USD/t")
            lines.append(f"- 最低: {stats.get('low', 'N/A')} USD/t")
            lines.append(f"- 均值: {stats.get('average', 'N/A')} USD/t")
            lines.append(f"- 涨跌: {stats.get('change', 'N/A')} USD/t ({stats.get('change_pct', 'N/A')}%)")

            points = price_trend.get("data_points", [])
            if points:
                lines.append("\n**最近 5 个交易日**:")
                for p in points[-5:]:
                    lines.append(f"- {p['date']}: {p['price']} USD/t")
    else:
        lines.append("30 日走势: 数据暂缺")

    return "\n".join(lines)


def build_risk_section(news: list[dict], price_trend: dict | None) -> str:
    risks = []

    # Check if price is trending down
    if price_trend and "statistics" in price_trend:
        change_pct = price_trend["statistics"].get("change_pct", 0)
        if isinstance(change_pct, (int, float)) and change_pct < 0:
            risks.append("⚠️ **锂价持续承压**: 30 日内锂价下跌 {:.1f}%，需关注下游需求变化和新增产能释放对价格的进一步影响。".format(abs(change_pct)))

    # Check for cost pressures in news
    for article in (news or []):
        summary = article.get("summary", "")
        if "成本" in summary or "劳动力" in summary:
            risks.append("⚠️ **运营成本上升**: 新闻提及西澳矿业劳动力成本上升，可能影响矿商利润率。Pilbara 凭借高品位优势成本控制较好，但行业整体面临压力。")
            break

    # Generic risk
    risks.append("⚠️ **下游需求不确定性**: 全球电动汽车增速放缓，锂盐库存水平仍处高位，短期供需格局难有根本性改善。")
    risks.append("ℹ️ **汇率风险**: 澳元/美元汇率波动会影响以澳元计价的运营成本和以美元计价的销售收入之间的匹配。")

    return "\n".join(risks)
