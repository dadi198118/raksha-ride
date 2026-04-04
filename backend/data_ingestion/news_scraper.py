"""
News Scraper: NewsAPI + GDELT + NDMA RSS
Polls for disaster-related news every 30 minutes via APScheduler.
In demo mode, uses mock headlines that realistically represent Indian disaster news.
"""
import httpx
import feedparser
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# Indian disaster keywords for NewsAPI query
DISASTER_KEYWORDS = [
    "curfew India", "Section 144", "bandh declared",
    "cyclone warning India", "flood alert India",
    "strike shutdown India", "IMD red alert",
    "NDMA disaster", "lockdown India"
]

# GDELT free API — no key required
GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"


async def fetch_newsapi(query: str, from_hours: int = 2) -> list[dict]:
    """Fetch recent news from NewsAPI matching query."""
    if not NEWSAPI_KEY:
        return []
    from_dt = (datetime.utcnow() - timedelta(hours=from_hours)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": from_dt,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "apiKey": NEWSAPI_KEY,
                }
            )
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                return [
                    {"title": a["title"], "source": "NewsAPI", "url": a["url"]}
                    for a in articles if a.get("title")
                ]
    except Exception as e:
        logger.warning(f"NewsAPI fetch failed: {e}")
    return []


async def fetch_gdelt(keyword: str) -> list[dict]:
    """Fetch from GDELT free API — no key required."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                GDELT_API,
                params={
                    "query": keyword,
                    "mode": "ArtList",
                    "maxrecords": 10,
                    "format": "json",
                    "timespan": "2h",
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                articles = data.get("articles", [])
                return [
                    {"title": a.get("title", ""), "source": "GDELT", "url": a.get("url", "")}
                    for a in articles if a.get("title")
                ]
    except Exception as e:
        logger.warning(f"GDELT fetch failed: {e}")
    return []


async def fetch_ndma_rss() -> list[dict]:
    """Fetch NDMA government disaster notification RSS feed."""
    try:
        feed = feedparser.parse("https://www.ndma.gov.in/rss.xml")
        return [
            {"title": e.get("title", ""), "source": "NDMA_RSS", "url": e.get("link", "")}
            for e in feed.entries[:15]
            if e.get("title")
        ]
    except Exception as e:
        logger.warning(f"NDMA RSS failed: {e}")
    return []


async def fetch_imd_rss() -> list[dict]:
    """IMD weather alerts RSS."""
    try:
        feed = feedparser.parse("https://mausam.imd.gov.in/imd_latest/contents/rss-feed.xml")
        return [
            {"title": e.get("title", ""), "source": "IMD_RSS", "url": e.get("link", "")}
            for e in feed.entries[:10]
            if e.get("title")
        ]
    except Exception as e:
        logger.warning(f"IMD RSS failed: {e}")
    return []


async def collect_all_news() -> list[dict]:
    """
    Aggregate all news sources. Returns deduplicated list of articles.
    In demo mode with no API key, returns empty (mock data in disruption_detection.py takes over).
    """
    import asyncio
    results = []

    tasks = [fetch_ndma_rss(), fetch_imd_rss()]

    if NEWSAPI_KEY:
        # Only fetch 2 keywords to stay within free tier (100 req/day)
        tasks += [fetch_newsapi(kw) for kw in DISASTER_KEYWORDS[:2]]

    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    for batch in gathered:
        if isinstance(batch, list):
            results.extend(batch)

    # Deduplicate by title
    seen = set()
    unique = []
    for item in results:
        t = item.get("title", "")[:80]
        if t and t not in seen:
            seen.add(t)
            unique.append(item)

    logger.info(f"News scraper collected {len(unique)} articles from {len(tasks)} sources")
    return unique