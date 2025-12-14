from datetime import datetime, timedelta
from typing import List, Dict, Any
import os
import logging

from flask import Flask, render_template, request, jsonify
import requests
import re

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")


def fetch_newsapi_articles(
    query: str,
    start: datetime,
    end: datetime,
    amount: int,
    sort_by: str = "popularity",
    language: str = "en",
) -> Dict[str, Any]:
    """Fetch articles from NewsAPI with pagination support."""
    api_key = os.environ.get("NEWSAPI_KEY")
    return fetch_newsapi_articles_with_key(query, start, end, amount, api_key, sort_by, language)


def fetch_newsapi_articles_with_key(
    query: str,
    start: datetime,
    end: datetime,
    amount: int,
    api_key: str,
    sort_by: str = "popularity",
    language: str = "en",
) -> Dict[str, Any]:
    """Fetch articles from NewsAPI with a provided API key."""
    if not api_key:
        return {"error": "NEWSAPI_KEY is missing"}

    page_size = min(100, amount)
    max_pages = (amount + page_size - 1) // page_size
    params_base = {
        "q": query,
        "language": language,
        "sortBy": sort_by,
        "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pageSize": page_size,
    }

    collected: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        params = {**params_base, "page": page}
        try:
            resp = requests.get(NEWSAPI_ENDPOINT, params=params, headers={"X-Api-Key": api_key}, timeout=10)
        except requests.RequestException as e:
            logger.error(f"NewsAPI request failed: {e}")
            return {"error": "Failed to reach NewsAPI"}

        if resp.status_code != 200:
            try:
                payload = resp.json()
                msg = payload.get("message")
            except Exception:
                msg = None
            logger.error(f"NewsAPI error {resp.status_code}: {msg}")
            return {"error": msg or f"NewsAPI error {resp.status_code}"}

        payload = resp.json()
        if payload.get("status") != "ok":
            return {"error": payload.get("message") or "NewsAPI returned an error"}

        articles = payload.get("articles", [])
        for art in articles:
            published_raw = art.get("publishedAt")
            if not published_raw:
                continue
            try:
                dt = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                continue
            collected.append({
                "title": art.get("title"),
                "link": art.get("url"),
                "published": dt,
                "source": (art.get("source") or {}).get("name"),
                "description": art.get("description") or "",
            })

        total_results = payload.get("totalResults") or 0
        if len(collected) >= amount:
            break
        if page * page_size >= total_results:
            break

    # Sort newest first
    collected.sort(key=lambda x: x["published"], reverse=True)
    return {"articles": collected[:amount]}


def filter_by_range(items: List[Dict[str, Any]], start: datetime, end: datetime) -> List[Dict[str, Any]]:
    return [i for i in items if start <= i["published"] <= end]


def filter_by_sources(items: List[Dict[str, Any]], sources: List[str]) -> List[Dict[str, Any]]:
    if not sources:
        return items
    # Case-insensitive partial matching
    sources_lower = [s.lower() for s in sources]
    filtered = []
    for item in items:
        source = (item.get("source") or "").lower()
        if any(s in source for s in sources_lower):
            filtered.append(item)
    return filtered


def bucket_by_day(items: List[Dict[str, Any]]) -> Dict[str, int]:
    buckets: Dict[str, int] = {}
    for i in items:
        key = i["published"].strftime("%Y-%m-%d")
        buckets[key] = buckets.get(key, 0) + 1
    return dict(sorted(buckets.items(), key=lambda kv: kv[0]))


STOPWORDS = set([
    "the","a","an","and","or","but","if","then","else","for","on","in","at","to","of","by","with","from","as",
    "is","are","was","were","be","been","being","this","that","these","those","about","over","under","after","before",
    "into","out","up","down","off","not","no","so","it","its","it's","their","his","her","him","she","he","they","them",
    "you","your","i","we","our","us"
])

# Source authority weights for importance scoring
SOURCE_AUTHORITY = {
    # Tier 1: Premium news sources (2.0x)
    "new york times": 2.0, "nyt": 2.0, "the new york times": 2.0,
    "bbc": 2.0, "bbc news": 2.0,
    "reuters": 2.0,
    "associated press": 2.0, "ap news": 2.0,
    "wall street journal": 2.0, "wsj": 2.0,
    "washington post": 2.0, "wapo": 2.0,
    "the guardian": 2.0, "guardian": 2.0,
    "financial times": 2.0, "ft": 2.0,
    
    # Tier 2: Major news networks (1.5x)
    "cnn": 1.5, "cnn news": 1.5,
    "fox news": 1.5,
    "nbc news": 1.5, "nbc": 1.5,
    "abc news": 1.5, "abc": 1.5,
    "cbs news": 1.5, "cbs": 1.5,
    "bloomberg": 1.5,
    "npr": 1.5,
    "usa today": 1.5,
    "the economist": 1.5, "economist": 1.5,
    
    # Tier 3: Other sources (1.0x) - default
}


def get_source_authority_weight(source: str) -> float:
    """Return authority weight for a news source."""
    if not source:
        return 1.0
    source_lower = source.lower()
    for key, weight in SOURCE_AUTHORITY.items():
        if key in source_lower:
            return weight
    return 1.0


def calculate_importance_score(cluster: List[Dict[str, Any]], period_start: datetime, period_end: datetime) -> float:
    """
    Calculate importance score for an article cluster using:
    - Coverage volume (40%)
    - Source diversity (25%)
    - Source authority (20%)
    - Temporal freshness (15%)
    """
    article_count = len(cluster)
    
    # Source diversity: count unique sources
    unique_sources = len(set(
        (art.get("source") or "unknown").lower() 
        for art in cluster
    ))
    
    # Authority-weighted count
    authority_score = sum(
        get_source_authority_weight(art.get("source"))
        for art in cluster
    )
    
    # Temporal freshness: articles closer to period end are "fresher"
    period_duration = (period_end - period_start).total_seconds()
    if period_duration > 0:
        freshness_scores = []
        for art in cluster:
            time_diff = (art["published"] - period_start).total_seconds()
            # Normalize to 0-1 (later in period = higher freshness)
            freshness = time_diff / period_duration
            freshness_scores.append(freshness)
        avg_freshness = sum(freshness_scores) / len(freshness_scores) if freshness_scores else 0.5
    else:
        avg_freshness = 0.5
    
    # Combined importance score
    importance = (
        article_count * 0.4 +
        unique_sources * 0.25 +
        authority_score * 0.2 +
        avg_freshness * 15 * 0.15  # Scale freshness to comparable range
    )
    
    return importance


def normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    tokens = [w for w in t.split() if len(w) >= 3 and w not in STOPWORDS]
    # keep first few informative tokens to form a canonical key
    return " ".join(tokens[:8])


def day_start(d: datetime) -> datetime:
    return datetime(d.year, d.month, d.day)


def week_start(d: datetime) -> datetime:
    # ISO week starts on Monday
    base = d - timedelta(days=d.weekday())
    return datetime(base.year, base.month, base.day)


def month_start(d: datetime) -> datetime:
    return datetime(d.year, d.month, 1)


def key_events_by_period(items: List[Dict[str, Any]], granularity: str) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for i in items:
        if granularity == "daily":
            ps = day_start(i["published"]).strftime("%Y-%m-%d")
        elif granularity == "monthly":
            ps = month_start(i["published"]).strftime("%Y-%m-%d")
        else:  # weekly default
            ps = week_start(i["published"]).strftime("%Y-%m-%d")
        buckets.setdefault(ps, []).append(i)

    result: List[Dict[str, Any]] = []
    for ps, arr in buckets.items():
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for art in arr:
            key = normalize_title(art.get("title") or "")
            if not key:
                key = art.get("title") or art.get("link") or "unknown"
            groups.setdefault(key, []).append(art)

        # Calculate period boundaries for freshness scoring
        period_start_dt = datetime.strptime(ps, "%Y-%m-%d")
        if granularity == "daily":
            period_end_dt = period_start_dt + timedelta(days=1)
        elif granularity == "monthly":
            # Next month start
            if period_start_dt.month == 12:
                period_end_dt = datetime(period_start_dt.year + 1, 1, 1)
            else:
                period_end_dt = datetime(period_start_dt.year, period_start_dt.month + 1, 1)
        else:  # weekly
            period_end_dt = period_start_dt + timedelta(days=7)

        # Score each cluster and pick the most important
        best_cluster: List[Dict[str, Any]] = []
        best_score = -1
        for cluster in groups.values():
            score = calculate_importance_score(cluster, period_start_dt, period_end_dt)
            if score > best_score:
                best_score = score
                best_cluster = cluster

        if not best_cluster:
            continue
        
        # Pick earliest article as representative
        rep = sorted(best_cluster, key=lambda x: x["published"])[0]

        # Create a concise summary (1-2 sentences) from cluster descriptions/titles
        summary = summarize_cluster(best_cluster, fallback_title=rep.get("title") or "")
        
        # Calculate source diversity and authority for display
        unique_sources = len(set(
            (art.get("source") or "unknown").lower() 
            for art in best_cluster
        ))
        avg_authority = sum(
            get_source_authority_weight(art.get("source"))
            for art in best_cluster
        ) / len(best_cluster)
        
        result.append({
            "periodStart": ps,
            "title": rep.get("title"),
            "link": rep.get("link"),
            "published": rep["published"].strftime("%Y-%m-%d %H:%M"),
            "clusterSize": len(best_cluster),
            "importanceScore": round(best_score, 2),
            "uniqueSources": unique_sources,
            "avgAuthority": round(avg_authority, 2),
            "summary": summary,
        })

    result.sort(key=lambda x: x["periodStart"])  # chronological
    return result


def summarize_cluster(cluster: List[Dict[str, Any]], fallback_title: str) -> str:
    """Return a 1-2 sentence summary from available descriptions.
    Strategy:
    - Prefer non-empty descriptions; pick the most informative (longest within limit)
    - If multiple, combine first sentences of top two descriptions
    - Fallback to the title if no description
    """
    descs = [c.get("description", "").strip() for c in cluster if c.get("description")]
    # Normalize whitespace
    descs = [re.sub(r"\s+", " ", d) for d in descs]
    if not descs:
        return fallback_title

    # Sort by length as proxy for informativeness
    descs.sort(key=len, reverse=True)

    def first_sentence(text: str) -> str:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return parts[0].strip() if parts else text.strip()

    s1 = first_sentence(descs[0])
    s2 = ""
    if len(descs) > 1:
        s2 = first_sentence(descs[1])
    # Avoid duplicate sentences
    if s2 and s2 != s1:
        combined = f"{s1} {s2}"
    else:
        combined = s1

    # Trim to ~280 chars to keep concise
    if len(combined) > 280:
        combined = combined[:277].rstrip() + "..."
    return combined


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"]) 
def search():
    data = request.get_json(force=True)
    
    # Get API key from request or environment
    api_key = (data.get("apiKey") or "").strip() or os.environ.get("NEWSAPI_KEY")
    
    query = (data.get("keyword") or "").strip()
    amount = int(data.get("amount") or 50)
    # NewsAPI: cap at 5000 per request
    if amount > 5000:
        amount = 5000
    # time_range: past_24_hours | past_week | past_month | past_year | custom
    time_range = data.get("timeRange") or "past_month"
    start_str = data.get("startDate")
    end_str = data.get("endDate")
    granularity = (data.get("granularity") or "weekly").lower()
    if granularity not in ("daily", "weekly", "monthly"):
        granularity = "weekly"
    sources = data.get("sources") or []  # List of source names to filter

    if not query:
        return jsonify({"error": "Keyword is required"}), 400
    
    if not api_key:
        return jsonify({"error": "NewsAPI key is required"}), 400

    # Compute date range
    today = datetime.utcnow()
    if time_range in ("past_24_hours", "last_1_day"):
        start = today - timedelta(days=1)
        end = today
    elif time_range in ("past_week", "last_7_days"):
        start = today - timedelta(days=7)
        end = today
    elif time_range in ("past_month", "last_30_days"):
        start = today - timedelta(days=30)
        end = today
    elif time_range in ("past_year", "last_365_days"):
        start = today - timedelta(days=365)
        end = today
    else:
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d") if start_str else today - timedelta(days=30)
            end = datetime.strptime(end_str, "%Y-%m-%d") if end_str else today
        except ValueError:
            return jsonify({"error": "Invalid custom dates"}), 400

    # Fetch from NewsAPI
    fetch_result = fetch_newsapi_articles_with_key(query, start, end, amount, api_key)
    if fetch_result.get("error"):
        return jsonify({"error": fetch_result["error"]}), 500

    entries = fetch_result.get("articles", [])
    
    # Filter by range (NewsAPI should already respect this, but double-check)
    filtered = filter_by_range(entries, start, end)
    # Filter by sources if specified
    filtered = filter_by_sources(filtered, sources)

    # Bucket by day for counts (still returned if needed)
    buckets = bucket_by_day(filtered)

    # Compute key events by selected granularity
    key_events = key_events_by_period(filtered, granularity)

    # Prepare article list to show
    articles = [
        {
            "title": e["title"],
            "link": e["link"],
            "published": e["published"].strftime("%Y-%m-%d %H:%M"),
            "source": e.get("source")
        }
        for e in filtered
    ]

    return jsonify({
        "timeline": buckets,
        "keyEvents": key_events,
        "granularity": granularity,
        "articles": articles,
        "range": {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d")
        }
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
