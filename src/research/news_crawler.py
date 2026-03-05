"""Secondary local-news analyzer (local-first, crawl as secondary)."""

from __future__ import annotations

from pathlib import Path

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
]


def analyze_news(company_dir: Path) -> dict:
    """Analyze local news docs and produce sentiment signals."""
    news_dir_candidates = [company_dir / "news_documents", company_dir / "news"]
    files = []
    for d in news_dir_candidates:
        if d.exists():
            files.extend(list_files(d))

    texts = []
    for f in files:
        try:
            texts.append(clean_text(f.read_text(encoding="utf-8", errors="ignore")))
        except Exception:
            continue

    joined = " ".join(texts).lower()
    neg_count = sum(joined.count(term) for term in NEGATIVE_TERMS)
    controversy = int("controversy" in joined or "allegation" in joined)
    distress = int("distress" in joined or "default" in joined)
    sentiment_score = max(0.0, 100.0 - (neg_count * 2.5 + controversy * 12 + distress * 15))

    return {
        "negative_news_count": int(neg_count),
        "controversy_mentions": int(controversy),
        "operational_distress": int(distress),
        "news_sentiment_score": round(float(sentiment_score), 2),
    }
