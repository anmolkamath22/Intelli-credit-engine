"""Litigation lookup from local docs and optional public-source search."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from src.utils.file_loader import list_files, read_json
from src.utils.text_processing import clean_text


def _search_indiankanoon(entity: str, max_hits: int = 5) -> list[dict]:
    q = urllib.parse.quote_plus(entity)
    url = f"https://indiankanoon.org/search/?formInput={q}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []
    out = []
    # Lightweight title/link extraction.
    for m in re.finditer(r'<a href="(/doc/\d+/)".*?>(.*?)</a>', text, flags=re.IGNORECASE | re.DOTALL):
        link = "https://indiankanoon.org" + m.group(1)
        title = re.sub(r"<.*?>", "", m.group(2)).strip()
        if title:
            out.append({"source": "indiankanoon", "title": title[:180], "link": link, "entity": entity})
        if len(out) >= max_hits:
            break
    return out


def lookup_litigation(company_dir: Path, company_name: str, board_members: list[str] | None = None) -> dict:
    """Estimate litigation risk from local legal docs + optional public-source lookup."""
    board_members = board_members or []
    legal_dir_candidates = [company_dir / "legal_documents", company_dir / "litigation_docs", company_dir / "legal"]
    files = []
    for d in legal_dir_candidates:
        if d.exists():
            files.extend(list_files(d))

    case_count = 0
    insolvency_flag = 0
    evidence: list[dict] = []

    for f in files:
        if f.suffix.lower() == ".json":
            payload = read_json(f)
            if payload:
                cc = int(payload.get("case_count", 0) or 0)
                case_count += cc
                insolvency_flag = max(insolvency_flag, int(bool(payload.get("insolvency_flag", False))))
                evidence.append(
                    {
                        "source": "local_legal_docs",
                        "title": f.name,
                        "date": "",
                        "entity": company_name,
                        "relevance_type": "litigation",
                        "summary": json.dumps(payload)[:350],
                        "risk_tag": "litigation_risk",
                    }
                )
        else:
            try:
                txt = clean_text(f.read_text(encoding="utf-8", errors="ignore")).lower()
            except Exception:
                continue
            cc = txt.count("case") + txt.count("petition") + txt.count("tribunal")
            case_count += cc
            insolvency_flag = max(insolvency_flag, int("insolvency" in txt or "nclt" in txt))
            evidence.append(
                {
                    "source": "local_legal_docs",
                    "title": f.name,
                    "date": "",
                    "entity": company_name,
                    "relevance_type": "litigation",
                    "summary": txt[:350],
                    "risk_tag": "litigation_risk",
                }
            )

    external = _search_indiankanoon(company_name, max_hits=6)
    for member in board_members[:4]:
        external.extend(_search_indiankanoon(member, max_hits=3))
    for x in external[:12]:
        case_count += 1
        evidence.append(
            {
                "source": x.get("source", "indiankanoon"),
                "title": x.get("title", ""),
                "date": "",
                "entity": x.get("entity", company_name),
                "relevance_type": "litigation",
                "summary": x.get("link", ""),
                "risk_tag": "litigation_risk",
                "url": x.get("link", ""),
            }
        )

    risk = min(100.0, case_count * 3.2 + insolvency_flag * 25)
    return {
        "litigation_count": int(case_count),
        "litigation_risk_score": round(float(risk), 2),
        "insolvency_flag": int(insolvency_flag),
        "case_summary": [e.get("summary", "") for e in evidence[:6]],
        "evidence": evidence[:40],
    }
