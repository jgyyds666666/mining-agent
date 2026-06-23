import json
import os
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mining-news", port=8001, host="0.0.0.0")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "news_samples.json")


def _load_news() -> list[dict]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _match_keyword(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


@mcp.tool()
def search(query: str, days: int = 7) -> str:
    """Search mining news articles by keyword and time range.

    Args:
        query: Search keywords, supports Chinese and English (e.g. 'Pilbara Minerals', 'lithium', '锂矿')
        days: Look back period in days (default 7, max 365)
    """
    keywords = query.split()
    articles = _load_news()

    # Date filter
    cutoff = datetime.now() - timedelta(days=days)

    results = []
    for art in articles:
        # Parse article date
        try:
            art_date = datetime.strptime(art["date"], "%Y-%m-%d")
        except ValueError:
            continue
        if art_date < cutoff:
            continue

        # Keyword match (title + source + summary)
        searchable = f"{art['title']} {art['source']} {art['summary']}"
        if not _match_keyword(searchable, keywords):
            continue

        results.append({
            "id": art["id"],
            "title": art["title"],
            "source": art["source"],
            "url": art["url"],
            "summary": art["summary"],
            "date": art["date"],
            "category": art["category"],
        })

    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def fetch_article(url: str) -> str:
    """Fetch the full content of a news article by its URL.

    Args:
        url: The article URL to fetch
    """
    articles = _load_news()
    for art in articles:
        if art["url"] == url:
            return json.dumps({
                "title": art["title"],
                "content": art["content"],
                "author": art["author"],
                "date": art["date"],
                "source": art["source"],
                "url": art["url"],
            }, ensure_ascii=False, indent=2)

    return json.dumps({
        "error": f"Article not found: {url}",
        "note": "The article database contains only demo samples. For real articles, please visit the source URL directly."
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="sse")
