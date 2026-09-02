"""Fetch a diversified cached market-news snapshot for the dashboard.

Reuters is the primary wire source. Bloomberg Markets and Financial Times
Markets add independent financial-market and macro context. Headlines are
deduplicated so one event reported by several outlets does not count as
several independent risk signals.
"""
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"

FEEDS = [
    {"name": "Reuters", "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20(global%20markets%20OR%20stocks%20OR%20bonds%20OR%20central%20banks)%20(oil%20OR%20inflation%20OR%20rates%20OR%20geopolitics)%26hl=en-US%26gl=US%26ceid=US:en", "priority": 1.15},
    {"name": "Bloomberg", "url": "https://feeds.bloomberg.com/markets/news.rss", "priority": 1.00},
    {"name": "Financial Times", "url": "https://www.ft.com/markets?format=rss", "priority": 1.00},
]

RISK_WORDS = {
    "war": 2, "attack": 2, "strike": 2, "conflict": 2, "iran": 2,
    "tariff": 2, "sanction": 2, "recession": 2, "selloff": 2,
    "sell-off": 2, "surge in yields": 2, "bond rout": 2,
    "inflation": 1, "oil": 1, "yield": 1, "bond": 1, "hawkish": 1,
    "rate hike": 1, "higher rates": 1, "deficit": 1, "downgrade": 1,
    "fear": 1, "tension": 1, "uncertainty": 1,
}
POS_WORDS = {
    "rally": 2, "rebound": 2, "rate cut": 1, "dovish": 1,
    "cooling inflation": 2, "strong earnings": 2, "growth": 1,
    "stimulus": 1, "recovery": 1, "gains": 1, "upgrade": 1,
}
STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "over",
    "after", "amid", "while", "what", "why", "how", "are", "its", "new",
    "global", "markets", "market", "stocks", "stock", "bonds", "bond",
}


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(title):
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if len(w) > 3 and w not in STOPWORDS}


def similar(a, b):
    aa, bb = tokenize(a), tokenize(b)
    if not aa or not bb:
        return False
    overlap = len(aa & bb) / max(1, min(len(aa), len(bb)))
    return overlap >= 0.55


def article_score(title):
    text = title.lower()
    risk = sum(weight for phrase, weight in RISK_WORDS.items() if phrase in text)
    positive = sum(weight for phrase, weight in POS_WORDS.items() if phrase in text)
    return max(-3, min(3, risk - positive)), risk, positive


def fetch_source(source):
    req = Request(source["url"], headers={"User-Agent": "GlobalMarketDashboard/2.0"})
    with urlopen(req, timeout=15) as response:
        root = ET.fromstring(response.read())

    articles = []
    for item in root.findall(".//item")[:15]:
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        published = clean(item.findtext("pubDate"))
        reported_source = clean(item.findtext("source")) or source["name"]
        if not title:
            continue
        score, risk, positive = article_score(title)
        articles.append({
            "title": title,
            "link": link,
            "published": published,
            "source": reported_source,
            "source_group": source["name"],
            "priority": source["priority"],
            "score": score,
            "risk": risk,
            "positive": positive,
        })
    return articles


def select_articles(raw):
    candidates = sorted(
        raw,
        key=lambda a: (abs(a["score"]) * a["priority"], a["priority"], a["published"]),
        reverse=True,
    )
    selected = []
    source_groups = set()

    for article in candidates:
        if any(similar(article["title"], existing["title"]) for existing in selected):
            continue
        # Build the first three slots from different outlets where possible.
        if article["source_group"] in source_groups and len(source_groups) < 3:
            continue
        selected.append(article)
        source_groups.add(article["source_group"])
        if len(selected) >= 5:
            break

    if len(selected) < 5:
        for article in candidates:
            if article in selected or any(similar(article["title"], x["title"]) for x in selected):
                continue
            selected.append(article)
            if len(selected) >= 5:
                break
    return selected


def classify(selected):
    if not selected:
        return "UNAVAILABLE"
    scores = [a["score"] for a in selected]
    negative = sum(s >= 1 for s in scores)
    positive = sum(s <= -1 for s in scores)
    risk_sources = len({a["source_group"] for a in selected if a["score"] >= 1})
    positive_sources = len({a["source_group"] for a in selected if a["score"] <= -1})
    if negative >= 3 and risk_sources >= 2 and sum(scores) >= 4:
        return "CAUTIOUS / RISK-OFF"
    if positive >= 3 and positive_sources >= 2 and sum(scores) <= -4:
        return "CAUTIOUS / RISK-ON"
    return "MIXED"


def build_summary(tone, selected):
    sources = len({a["source_group"] for a in selected})
    themes = len(selected)
    if tone == "CAUTIOUS / RISK-OFF":
        lead = "Multiple independent sources are highlighting meaningful macro or geopolitical risks."
    elif tone == "CAUTIOUS / RISK-ON":
        lead = "Multiple independent sources are highlighting improving growth, inflation or market conditions."
    else:
        lead = "News is mixed across the main market and macro themes."
    return f"{lead} {themes} distinct headlines from {sources} source groups are used; market indicators remain the primary signal."


def fetch():
    raw = []
    failures = []
    for source in FEEDS:
        try:
            raw.extend(fetch_source(source))
        except Exception as exc:
            failures.append(f"{source['name']}: {exc}")
            print(f"News source unavailable — {source['name']}: {exc}")

    if not raw:
        raise RuntimeError("All news sources unavailable")

    selected = select_articles(raw)
    tone = classify(selected)
    articles = [
        {k: a[k] for k in ("title", "link", "published", "source", "source_group")}
        for a in selected
    ]
    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tone": tone,
        "summary": build_summary(tone, selected),
        "sources": sorted({a["source_group"] for a in selected}),
        "articles": articles,
    }
    if failures:
        payload["source_warnings"] = failures
    return payload


def main():
    try:
        payload = fetch()
    except Exception as exc:
        print(f"News fetch unavailable: {exc}")
        if OUT.exists():
            return
        payload = {
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "tone": "UNAVAILABLE",
            "summary": "News feed unavailable; market indicators remain the primary signal.",
            "sources": [],
            "articles": [],
        }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
