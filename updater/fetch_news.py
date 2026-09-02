"""Fetch a small cached market-news snapshot for the dashboard.

The browser reads data/news.json rather than calling a news service directly.
GitHub Actions refreshes this file on the normal dashboard schedule.
"""
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
FEED = (
    "https://news.google.com/rss/search?"
    "q=site%3Areuters.com%20(global%20markets%20OR%20stocks%20OR%20bonds)%20"
    "(oil%20OR%20inflation%20OR%20rates%20OR%20geopolitics)"
    "&hl=en-US&gl=US&ceid=US:en"
)

RISK_WORDS = re.compile(r"oil|inflation|yield|bond|war|iran|tariff|sanction|recession|selloff|hawkish|tighten|risk", re.I)
POS_WORDS = re.compile(r"earnings|growth|rally|strong|rebound|cooling inflation|dovish|rate cut|stimulus", re.I)


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def fetch():
    req = Request(FEED, headers={"User-Agent": "GlobalMarketDashboard/2.0"})
    with urlopen(req, timeout=15) as r:
        root = ET.fromstring(r.read())

    articles = []
    for item in root.findall(".//item")[:8]:
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        pub = clean(item.findtext("pubDate"))
        source = clean(item.findtext("source")) or "Reuters"
        if not title:
            continue
        articles.append({"title": title, "link": link, "published": pub, "source": source})

    if not articles:
        raise RuntimeError("No news items returned")

    risk = sum(bool(RISK_WORDS.search(a["title"])) for a in articles[:5])
    positive = sum(bool(POS_WORDS.search(a["title"])) for a in articles[:5])
    tone = "CAUTIOUS / RISK-OFF" if risk > positive else "MIXED" if risk == positive else "CAUTIOUS / RISK-ON"

    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tone": tone,
        "summary": "Headline context is used as a macro overlay; market indicators remain the primary signal.",
        "articles": articles[:5],
    }


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
            "articles": [],
        }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
