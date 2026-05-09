"""
vector_store.py — Text utilities for scholarship semantic retrieval.

Provides:
  - build_text_for_scholarship() : builds a flat text summary of a scholarship
  - simple_text_similarity()     : deterministic difflib fallback
  - llm_semantic_rank()          : ONE batch LLM call that ranks all scholarships
                                   against a profile — replaces ChromaDB/embeddings
"""
from __future__ import annotations

import difflib
import json
import re


def build_text_for_scholarship(scholarship: dict) -> str:
    """Flat text representation of a scholarship for comparison / LLM input."""
    parts = [
        scholarship.get("scholarship_name"),
        scholarship.get("institution"),
        scholarship.get("country"),
        scholarship.get("academic_level"),
        " ".join(scholarship.get("fields", [])),
        " ".join(scholarship.get("benefits", [])),
        " ".join(scholarship.get("eligible_nationalities", [])),
        " ".join(scholarship.get("required_languages", [])),
        " ".join(scholarship.get("requirements", [])),
    ]
    return " ".join(str(part).strip() for part in parts if part).strip()


def simple_text_similarity(profile_text: str, scholarship_text: str) -> int:
    """
    Deterministic fallback similarity (0-100) using difflib.
    Used when semantic search is disabled or the LLM call fails.
    """
    if not profile_text or not scholarship_text:
        return 0
    ratio = difflib.SequenceMatcher(
        None,
        profile_text.casefold(),
        scholarship_text.casefold(),
    ).ratio()
    return max(0, min(100, int(round(ratio * 100))))


def llm_semantic_rank(
    profile_text: str,
    scholarships: list[dict],
    top_k: int = 20,
) -> list[dict]:
    """
    Send the student profile + scholarship summaries to the configured LLM
    in a SINGLE batch call and get back semantically ranked results.

    This replaces ChromaDB / vector embeddings entirely — the language model
    acts as the semantic similarity engine.

    Args:
        profile_text: Flat text description of the student profile.
        scholarships:  List of deserialized scholarship dicts.
        top_k:         How many top results to request from the LLM.

    Returns:
        List of dicts sorted by semantic_score desc:
          [{"index": int, "semantic_score": int (0-100), "reason": str}, ...]
        Returns [] on any error — caller falls back to deterministic scoring.
    """
    if not scholarships or not profile_text.strip():
        return []

    # Build compact summaries (cap at 300 chars each to keep prompt size manageable)
    summaries: list[str] = []
    for i, s in enumerate(scholarships[:40]):  # max 40 scholarships per batch
        text = build_text_for_scholarship(s)
        summaries.append(f"[{i}] {text[:300]}")

    effective_top_k = min(top_k, len(scholarships))

    prompt = (
        "You are a scholarship eligibility expert.\n\n"
        "Student profile:\n"
        f"{profile_text}\n\n"
        f"Rate each scholarship's semantic relevance to this student profile (0–100).\n"
        "Consider: field of study alignment, academic level, country preferences,\n"
        "nationality eligibility, language requirements, and benefit type\n"
        "(fully funded, stipend, tuition waiver, etc.).\n\n"
        f"Return a JSON array of the top {effective_top_k} most relevant scholarships:\n"
        '[{"index": 0, "semantic_score": 85, "reason": "short reason max 1 sentence"}, ...]\n\n'
        "Output ONLY the JSON array. No markdown. No explanation.\n\n"
        "Scholarships:\n"
        + "\n".join(summaries)
    )

    try:
        from llm.provider import generate_text  # inline import avoids circular deps

        raw = generate_text(prompt)

        # Extract JSON array robustly — the LLM may wrap it in markdown
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if not match:
            return []

        ranked: list[dict] = json.loads(match.group())
        results: list[dict] = []

        for item in ranked:
            idx = item.get("index")
            score = item.get("semantic_score", 0)
            reason = str(item.get("reason", ""))
            if not isinstance(idx, int) or not (0 <= idx < len(scholarships)):
                continue
            results.append({
                "index": idx,
                "semantic_score": max(0, min(100, int(score))),
                "reason": reason[:200],
            })

        return sorted(results, key=lambda x: x["semantic_score"], reverse=True)

    except Exception:
        # Any failure → caller falls back to deterministic difflib scoring
        return []
