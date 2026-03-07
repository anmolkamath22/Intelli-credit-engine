"""News intelligence with local + external-source fallback."""

from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

from src.utils.file_loader import list_files
from src.utils.text_processing import clean_text

NEGATIVE_TERMS = [
    "fraud",
    "default",
    "downgrade",
    "penalty",
    "investigation",
    "distress",
    "delay",
    "insolvency",
    "loss",
    "controversy",
    "regulatory",
    "shutdown",
    "layoff",
]


def _fetch_google_news_rss(query: str, max_items: int = 10) -> list[dict]:
    q = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={q}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            xml_data = resp.read()
    except Exception:
        return []
    out: list[dict] = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item")[:max_items]:
            out.append(
                {
                    "source": "google_news_rss",
                    "title": html.unescape(item.findtext("title", default="")),
                    "link": item.findtext("link", default=""),
                    "date": item.findtext("pubDate", default=""),
                    "summary": html.unescape(item.findtext("description", default="")),
                    "query": query,
                }
            )
    except Exception:
        return []
    return out


def _risk_tag(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["fraud", "investigation", "enforcement"]):
        return "regulatory_risk"
    if any(x in t for x in ["default", "insolvency", "distress"]):
        return "financial_distress"
    if any(x in t for x in ["controversy", "allegation"]):
        return "reputation_risk"
    return "sector_headwind"


def analyze_news(company_dir: Path, company_name: str, board_members: list[str] | None = None) -> dict:
    """Analyze local and optional external news for risk signals."""
    board_members = board_members or []
    news_dir_candidates = [company_dir / "news_documents", company_dir / "news"]
    local_files = []
    for d in news_dir_candidates:
        if d.exists():
            local_files.extend(list_files(d))

    local_evidence = []
    text_blob = ""
    for f in local_files:
        try:
            txt = clean_text(f.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        text_blob += " " + txt
        local_evidence.append(
            {
                "source": "local_news_docs",
                "title": f.name,
                "date": "",
                "entity": company_name,
                "relevance_type": "news",
                "summary": txt[:350],
                "risk_tag": _risk_tag(txt),
            }
        )

    external_articles = _fetch_google_news_rss(company_name, max_items=8)
    for member in board_members[:4]:
        external_articles.extend(_fetch_google_news_rss(f"{member} {company_name} controversy litigation", max_items=4))

    external_evidence = []
    for a in external_articles[:15]:
        content = f"{a.get('title', '')} {a.get('summary', '')}"
        entity = company_name
        q = str(a.get("query", ""))
        for member in board_members[:8]:
            if member.lower() in q.lower():
                entity = member
                break
        external_evidence.append(
            {
                "source": a.get("source", "google_news_rss"),
                "title": a.get("title", ""),
                "date": a.get("date", ""),
                "entity": entity,
                "relevance_type": "news",
                "summary": content[:350],
                "risk_tag": _risk_tag(content),
                "url": a.get("link", ""),
            }
        )
        text_blob += " " + content

    joined = text_blob.lower()
    neg_count = sum(joined.count(term) for term in NEGATIVE_TERMS)
    controversy = int(bool(re.search(r"controversy|allegation|probe", joined)))
    distress = int(bool(re.search(r"default|insolvency|distress|shutdown", joined)))
    sentiment_score = max(0.0, 100.0 - (neg_count * 2.2 + controversy * 10 + distress * 14))

    return {
        "negative_news_count": int(neg_count),
        "controversy_mentions": int(controversy),
        "operational_distress": int(distress),
        "news_sentiment_score": round(float(sentiment_score), 2),
        "evidence": (local_evidence + external_evidence)[:30],
    }
