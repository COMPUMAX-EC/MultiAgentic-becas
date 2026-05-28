"""scholarship_search.py — Semantic search using the LLM (no RAG/ChromaDB)."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from database.repository import list_recent_scholarships


def _parse_list(val) -> list[str]:
    if isinstance(val, list): return [str(v) for v in val]
    try:
        p = json.loads(val or "[]")
        return [str(v) for v in p] if isinstance(p, list) else []
    except Exception:
        return []


def _summary(s: dict) -> str:
    fields = _parse_list(s.get("fields_json") or s.get("fields", []))
    nats   = _parse_list(s.get("eligible_nationalities_json") or s.get("eligible_nationalities", []))
    langs  = _parse_list(s.get("required_languages_json") or s.get("required_languages", []))
    return (f"Name: {s.get('scholarship_name','')}\nInstitution: {s.get('institution','')}\n"
            f"Country: {s.get('country','')}\nLevel: {s.get('academic_level','')}\n"
            f"Fields: {', '.join(fields)}\nNationalities: {', '.join(nats)}\n"
            f"Languages: {', '.join(langs)}\nStatus: {s.get('application_status','')}")


def semantic_search_scholarships(
    query: str,
    limit: int = 50,
    top_k: int = 10,
    profile: dict | None = None,
) -> list[dict]:
    all_s = list_recent_scholarships(limit=limit)
    if not all_s:
        return []
    if not query.strip():
        return all_s[:top_k]

    student_block = query.strip()
    if profile:
        student_block = (
            "Student profile:\n"
            f"{query.strip()}\n\n"
            "Rank scholarships by fit with this profile."
        )

    summaries = [f"[{i+1}] {_summary(s)}" for i, s in enumerate(all_s)]
    prompt = (f'You are a scholarship advisor. Student context:\n"""{student_block}"""\n\n'
              f"Select the top {top_k} most relevant scholarships.\n"
              'Return JSON array: [{"index": <1-based>, "relevance_reason": "..."}, ...]\n'
              "Output ONLY the JSON array.\n\nScholarships:\n" + "\n".join(summaries[:40]))
    try:
        from llm.provider import generate_text
        raw = generate_text(prompt)
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return all_s[:top_k]
        ranked = json.loads(match.group())
        results = []
        for item in ranked[:top_k]:
            idx = int(item.get("index", 0)) - 1
            if 0 <= idx < len(all_s):
                s = dict(all_s[idx])
                s["relevance_reason"] = item.get("relevance_reason", "")
                results.append(s)
        return results
    except Exception:
        return all_s[:top_k]
