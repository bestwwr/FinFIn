import feedparser
import re
from datetime import datetime, timedelta
from typing import List, Dict

RSS_FEEDS = [
    {"name": "Reuters Business", "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "Yahoo Finance",    "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "CNBC Finance",     "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html"},
    {"name": "Bangkok Post Biz", "url": "https://www.bangkokpost.com/rss/data/business.xml"},
    {"name": "Investing.com",    "url": "https://www.investing.com/rss/news_25.rss"},
]

FALLBACK_FEEDS = [
    {"name": "MarketWatch",  "url": "https://feeds.marketwatch.com/marketwatch/topstories/"},
    {"name": "Seeking Alpha","url": "https://seekingalpha.com/feed.xml"},
]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _fetch_from_feeds(feeds: List[Dict], max_per_feed: int, cutoff: datetime) -> List[Dict]:
    articles = []
    for feed_info in feeds:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:max_per_feed]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                if published and published < cutoff:
                    continue

                articles.append({
                    "source":    feed_info["name"],
                    "title":     _strip_html(entry.get("title", "")),
                    "summary":   _strip_html(entry.get("summary", entry.get("description", "")))[:400],
                    "link":      entry.get("link", ""),
                    "published": published.strftime("%Y-%m-%d %H:%M") if published else "N/A",
                })
        except Exception as e:
            print(f"[fetcher] Error on {feed_info['name']}: {e}")
    return articles


def fetch_news(min_articles: int = 5, max_per_feed: int = 5, hours_back: int = 18) -> List[Dict]:
    cutoff = datetime.now() - timedelta(hours=hours_back)

    # Primary sources
    articles = _fetch_from_feeds(RSS_FEEDS, max_per_feed, cutoff)

    # Decision: ถ้าน้อยกว่า min → ลอง fallback sources
    if len(articles) < min_articles:
        print(f"[fetcher] Only {len(articles)} articles found, trying fallback sources...")
        fallback = _fetch_from_feeds(FALLBACK_FEEDS, max_per_feed, cutoff)
        articles += fallback
        print(f"[fetcher] After fallback: {len(articles)} articles total.")

    return articles
