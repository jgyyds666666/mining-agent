import json
import os
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lme-price")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "lme_prices.json")


def _load_prices() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@mcp.tool()
def get_price(commodity: str, date: str = "today") -> str:
    """Get the latest price for a commodity.

    Args:
        commodity: Commodity name — supported: 'lithium', 'lithium_carbonate',
                   'spodumene', 'lce', '碳酸锂', '锂'
        date: Date in YYYY-MM-DD format, or 'today' (default) / 'latest'
    """
    data = _load_prices()

    # Normalize commodity name — accept any lithium alias
    lithium_aliases = {"lithium", "lithium_carbonate", "spodumene",
                       "lce", "碳酸锂", "锂", "碳酸锂"}
    if commodity.lower() not in lithium_aliases:
        return json.dumps({
            "error": f"Commodity '{commodity}' not supported.",
            "supported_commodities": ["lithium", "lithium_carbonate",
                                       "spodumene", "lce", "碳酸锂", "锂"]
        }, ensure_ascii=False, indent=2)

    points = data["data_points"]

    # Determine target date
    if date in ("today", "latest"):
        target = max(p["date"] for p in points)
    else:
        target = date

    # Find matching price
    for p in points:
        if p["date"] == target:
            return json.dumps({
                "commodity": data["display_name"],
                "unit": data["unit"],
                "date": p["date"],
                "price": p["price"],
                "currency": data["currency"],
            }, ensure_ascii=False, indent=2)

    return json.dumps({
        "error": f"Price data not available for date: {target}",
        "available_date_range": f"{points[0]['date']} ~ {points[-1]['date']}"
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def get_trend(commodity: str, days: int = 30) -> str:
    """Get the price trend for a commodity over a given period.

    Args:
        commodity: Commodity name (e.g. 'lithium', '碳酸锂')
        days: Look-back period in days (default 30, max 365)
    """
    data = _load_prices()

    # Normalize commodity name
    lithium_aliases = {"lithium", "lithium_carbonate", "spodumene",
                       "lce", "碳酸锂", "锂", "碳酸锂"}
    if commodity.lower() not in lithium_aliases:
        return json.dumps({
            "error": f"Commodity '{commodity}' not supported.",
            "supported_commodities": ["lithium", "lithium_carbonate",
                                       "spodumene", "lce", "碳酸锂", "锂"]
        }, ensure_ascii=False, indent=2)

    points = data["data_points"]
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    filtered = [p for p in points if p["date"] >= cutoff_str]
    stats = data["statistics_30d"]

    result = {
        "commodity": data["display_name"],
        "unit": data["unit"],
        "currency": data["currency"],
        "period": f"{days} days",
        "data_points": filtered,
        "statistics": stats,
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="sse", port=8003)
