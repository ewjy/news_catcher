from datetime import datetime, timedelta
from typing import List, Dict, Any
import os

from flask import Flask, render_template, request, jsonify
import feedparser
import re

app = Flask(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def parse_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed = []
    for e in entries:
        # published_parsed is a time.struct_time
        pub = e.get("published_parsed") or e.get("updated_parsed")
        if not pub:
            # Skip items without a date
            continue
        dt = datetime(*pub[:6])
        parsed.append({
            "title": e.get("title"),
            "link": e.get("link"),
            "published": dt,
            "source": e.get("source", {}).get("title") if isinstance(e.get("source"), dict) else None
        })
    return parsed


def filter_by_range(items: List[Dict[str, Any]], start: datetime, end: datetime) -> List[Dict[str, Any]]:
    return [i for i in items if start <= i["published"] <= end]


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

        # pick group with most items
        top_items: List[Dict[str, Any]] = []
        for g in groups.values():
            if len(g) > len(top_items):
                top_items = g
            elif len(g) == len(top_items) and top_items:
                g_earliest = min(x["published"] for x in g)
                t_earliest = min(x["published"] for x in top_items)
                if g_earliest < t_earliest:
                    top_items = g

        if not top_items:
            continue
        rep = sorted(top_items, key=lambda x: x["published"])[0]
        result.append({
            "periodStart": ps,
            "title": rep.get("title"),
            "link": rep.get("link"),
            "published": rep["published"].strftime("%Y-%m-%d %H:%M"),
            "clusterSize": len(top_items)
        })

    result.sort(key=lambda x: x["periodStart"])  # chronological
    return result


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"]) 
def search():
    data = request.get_json(force=True)
    query = (data.get("keyword") or "").strip()
    amount = int(data.get("amount") or 50)
    # allow up to 2000 requested; actual returned depends on RSS availability
    if amount > 2000:
        amount = 2000
    # time_range: past_24_hours | past_week | past_month | past_year | custom (also accept old values)
    time_range = data.get("timeRange") or "past_month"
    start_str = data.get("startDate")
    end_str = data.get("endDate")
    granularity = (data.get("granularity") or "weekly").lower()
    if granularity not in ("daily", "weekly", "monthly"):
        granularity = "weekly"

    if not query:
        return jsonify({"error": "Keyword is required"}), 400

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

    # Build RSS URL and fetch
    # Google News RSS returns recent results; we will filter client-side by date
    url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))
    feed = feedparser.parse(url)

    if feed.bozo:
        return jsonify({"error": "Failed to fetch Google News RSS"}), 500

    entries = parse_entries(feed.entries)
    # Sort by published desc then trim to amount
    entries.sort(key=lambda x: x["published"], reverse=True)
    entries = entries[:amount]
    # Filter by range
    filtered = filter_by_range(entries, start, end)

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
