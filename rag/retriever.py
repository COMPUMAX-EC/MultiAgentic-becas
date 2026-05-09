"""
retriever.py — Scholarship retrieval using LLM-based semantic search.

Architecture (integrated, no HTTP microservice):

  SQLite KB ──► pre-filter (skip closed/expired) ──► deterministic scoring
                                                            │
                                                  SEMANTIC_SEARCH_ENABLED?
                                                     │           │
                                                    YES          NO
                                                     │           │
                                              llm_semantic_rank  │
                                              (single LLM call)  │
                                                     │           │
                                              merge scores ◄─────┘
                                                     │
                                              top-K results

The LLM semantic rank replaces ChromaDB/embeddings entirely.
Deterministic field scores (country, level, nationality) are always computed
and blended with the LLM semantic score for robustness.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from config.settings import settings
from database.repository import list_recent_scholarships
from rag.vector_store import (
    build_text_for_scholarship,
    llm_semantic_rank,
    simple_text_similarity,
)
from schemas.retrieval_schema import RetrievalValidationError, build_retrieval_result
from utils.logger import get_logger
from utils.normalizer import (
    normalize_academic_level,
    normalize_country,
    normalize_language_entries,
    normalize_list,
    normalize_text,
)

logger = get_logger(__name__)


class ScholarshipRetriever:
    def __init__(self) -> None:
        self.skipped_closed_or_expired = 0

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def retrieve(self, normalized_profile: dict) -> list[dict]:
        """
        Main retrieval method.

        1. Load scholarships from SQLite.
        2. Pre-filter closed/expired.
        3. If SEMANTIC_SEARCH_ENABLED → single LLM batch call for semantic scores.
        4. Compute deterministic scores (country, level, nationality, language).
        5. Blend scores → sort → return top-K.
        """
        fetch_limit = max(settings.RETRIEVAL_MAX_RESULTS * 5, 50)
        all_rows = list_recent_scholarships(limit=fetch_limit)

        # Deserialize all rows
        scholarships: list[dict] = []
        self.skipped_closed_or_expired = 0
        for row in all_rows:
            s = self._deserialize_row(row)
            if self._should_skip(s):
                self.skipped_closed_or_expired += 1
                continue
            scholarships.append(s)

        if not scholarships:
            return []

        # ── Build profile text for similarity ─────────────────────────────────
        profile_text = self._build_profile_text(normalized_profile)

        # ── LLM semantic ranking (one batch call) ──────────────────────────────
        semantic_map: dict[int, dict] = {}   # index → {semantic_score, reason}

        if settings.SEMANTIC_SEARCH_ENABLED:
            logger.info(
                "Running LLM semantic ranking over %d scholarships (top_k=%d)",
                len(scholarships),
                settings.SEMANTIC_SEARCH_TOP_K,
            )
            try:
                ranked = llm_semantic_rank(
                    profile_text=profile_text,
                    scholarships=scholarships,
                    top_k=settings.SEMANTIC_SEARCH_TOP_K,
                )
                for item in ranked:
                    semantic_map[item["index"]] = item
                logger.info(
                    "LLM semantic ranking returned %d scored scholarships", len(ranked)
                )
            except Exception as exc:
                logger.warning("LLM semantic ranking failed, using fallback: %s", exc)

        # ── Score every scholarship ────────────────────────────────────────────
        scored: list[dict] = []
        for idx, scholarship in enumerate(scholarships):
            result = self._score_scholarship(
                normalized_profile=normalized_profile,
                scholarship=scholarship,
                profile_text=profile_text,
                semantic_item=semantic_map.get(idx),
            )
            if result["retrieval_score"] >= settings.RETRIEVAL_MIN_SCORE:
                scored.append(result)

        # Sort by score desc, break ties by source reliability
        scored.sort(
            key=lambda r: (r["retrieval_score"], r.get("source_reliability_score", 0)),
            reverse=True,
        )
        return scored[: settings.RETRIEVAL_MAX_RESULTS]

    # ──────────────────────────────────────────────────────────────────────────
    # Scoring
    # ──────────────────────────────────────────────────────────────────────────

    def _score_scholarship(
        self,
        normalized_profile: dict,
        scholarship: dict,
        profile_text: str,
        semantic_item: dict | None,
    ) -> dict:
        """
        Blend deterministic field scores with the LLM semantic score.

        Score budget:
          Country match          25 pts  (deterministic)
          Field/interests match  25 pts  (deterministic)
          Academic level match   20 pts  (deterministic)
          Nationality match      10 pts  (deterministic)
          Language match         10 pts  (deterministic)
          Reliability bonus      10 pts  (deterministic)
          ─────────────────────────────
          Deterministic subtotal 100 pts (but capped weights below)

          Semantic bonus         up to +30 pts  (LLM score / 100 * 30)
          Fallback text bonus    up to +10 pts  (difflib, only when LLM unavailable)
        """
        profile_targets = {
            c.casefold()
            for c in normalize_list(normalized_profile.get("target_countries"))
        }
        profile_field    = normalize_text(normalized_profile.get("field_of_study")) or ""
        profile_interests = normalize_list(normalized_profile.get("interests"))
        profile_level    = normalize_academic_level(normalized_profile.get("academic_level"))
        profile_nationality = normalize_country(normalized_profile.get("nationality"))
        profile_languages = {
            lang.casefold()
            for lang in normalize_language_entries(normalized_profile.get("languages"))
        }

        s_country  = normalize_country(scholarship.get("country"))
        s_level    = normalize_academic_level(scholarship.get("academic_level"))
        s_fields   = normalize_list(scholarship.get("fields"))
        s_nats     = normalize_list(scholarship.get("eligible_nationalities"))
        s_langs    = normalize_language_entries(scholarship.get("required_languages"))

        score  = 0
        reasons: list[str] = []

        # Country
        if s_country and s_country.casefold() in profile_targets:
            score += 25
            reasons.append("Target country matches the profile.")

        # Field
        if self._field_match(profile_field, profile_interests, s_fields):
            score += 25
            reasons.append("Field of study or interests align with the scholarship.")

        # Academic level
        if profile_level and s_level and profile_level.casefold() == s_level.casefold():
            score += 20
            reasons.append("Academic level matches.")

        # Nationality
        if profile_nationality and self._nationality_match(profile_nationality, s_nats):
            score += 10
            reasons.append("Nationality appears compatible with eligibility.")

        # Language
        if s_langs and self._language_match(profile_languages, s_langs):
            score += 10
            reasons.append("Language requirements appear compatible.")

        # Source reliability bonus (max +10)
        reliability = self._clamp(scholarship.get("source_reliability_score"))
        reliability_bonus = min(10, reliability // 10)
        if reliability_bonus:
            score += reliability_bonus
            reasons.append("Source reliability improves confidence.")

        # ── Semantic score ─────────────────────────────────────────────────────
        if semantic_item is not None:
            # LLM gave a score: scale to +30 bonus pts maximum
            sem_score = semantic_item.get("semantic_score", 0)
            sem_bonus = round(sem_score / 100 * 30)
            score += sem_bonus
            reason_text = semantic_item.get("reason", "")
            if reason_text:
                reasons.append(f"LLM semantic match: {reason_text}")
            elif sem_bonus:
                reasons.append(f"LLM semantic relevance score: {sem_score}/100.")
        else:
            # Fallback: difflib text similarity (max +10 pts)
            scholarship_text = build_text_for_scholarship(scholarship)
            sim = simple_text_similarity(profile_text, scholarship_text)
            sim_bonus = min(10, sim // 10)
            if sim_bonus:
                score += sim_bonus
                reasons.append("Profile text similarity provides a small bonus.")

        # Upcoming deadline bonus
        status = str(scholarship.get("application_status") or "unknown").strip().lower()
        if status == "upcoming":
            score += 3
            reasons.append("Application cycle appears upcoming.")
        elif status == "unknown":
            score -= 5
            reasons.append("Application status is uncertain.")

        return build_retrieval_result(
            scholarship_name=scholarship.get("scholarship_name"),
            source_url=scholarship.get("source_url"),
            institution=scholarship.get("institution"),
            country=scholarship.get("country"),
            academic_level=scholarship.get("academic_level"),
            fields=scholarship.get("fields"),
            benefits=scholarship.get("benefits"),
            deadline=scholarship.get("deadline"),
            application_status=scholarship.get("application_status"),
            retrieval_score=score,
            retrieval_reasons=reasons,
            source_reliability_score=reliability,
            eligible_nationalities=scholarship.get("eligible_nationalities", []),
            required_languages=scholarship.get("required_languages", []),
            requirements=scholarship.get("requirements", []),
            source_type=scholarship.get("source_type"),
            extraction_confidence=scholarship.get("extraction_confidence"),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _deserialize_row(self, row: dict) -> dict:
        return {
            "scholarship_name":       row.get("scholarship_name"),
            "institution":            row.get("institution"),
            "country":                row.get("country"),
            "academic_level":         row.get("academic_level"),
            "eligible_nationalities": self._json_list(row.get("eligible_nationalities_json")),
            "required_languages":     self._json_list(row.get("required_languages_json")),
            "fields":                 self._json_list(row.get("fields_json")),
            "benefits":               self._json_list(row.get("benefits_json")),
            "deadline":               row.get("deadline"),
            "requirements":           self._json_list(row.get("requirements_json")),
            "application_status":     row.get("application_status"),
            "source_url":             row.get("source_url"),
            "source_type":            row.get("source_type"),
            "source_reliability_score": row.get("source_reliability_score"),
            "extraction_confidence":  row.get("extraction_confidence"),
        }

    def _json_list(self, value: object) -> list[str]:
        if isinstance(value, list):
            return normalize_list(value)
        if not isinstance(value, str) or not value.strip():
            return []
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return normalize_list(loaded)

    def _should_skip(self, scholarship: dict) -> bool:
        status = str(scholarship.get("application_status") or "unknown").strip().lower()
        if status == "closed":
            return True
        deadline_text = normalize_text(scholarship.get("deadline"))
        if not deadline_text:
            return False
        return self._deadline_is_expired(deadline_text)

    def _deadline_is_expired(self, deadline_text: str) -> bool:
        formats = (
            "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y",
            "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        )
        for fmt in formats:
            try:
                return datetime.strptime(deadline_text, fmt).date() < datetime.now(timezone.utc).date()
            except ValueError:
                continue
        return False

    def _field_match(
        self, profile_field: str, profile_interests: list[str], scholarship_fields: list[str]
    ) -> bool:
        text = " ".join(scholarship_fields).casefold()
        if profile_field and profile_field.casefold() in text:
            return True
        if any(i.casefold() in text for i in profile_interests):
            return True
        if profile_field and self._is_stem(profile_field) and self._is_stem(text):
            return True
        return False

    def _nationality_match(self, profile_nationality: str, s_nats: list[str]) -> bool:
        if not s_nats:
            return False
        key = profile_nationality.casefold()
        broad = ("international", "all nationalities", "all countries", "open to all")
        for nat in s_nats:
            nat_key = nat.casefold()
            if nat_key == key or key in nat_key:
                return True
            if any(b in nat_key for b in broad):
                return True
        return False

    def _language_match(self, profile_langs: set[str], s_langs: list[str]) -> bool:
        for lang in s_langs:
            if any(pl in lang.casefold() for pl in profile_langs):
                return True
        return False

    def _build_profile_text(self, profile: dict) -> str:
        parts = [
            profile.get("nationality"),
            profile.get("country_of_residence"),
            profile.get("academic_level"),
            profile.get("field_of_study"),
            " ".join(normalize_list(profile.get("interests"))),
            " ".join(normalize_list(profile.get("target_countries"))),
            " ".join(normalize_language_entries(profile.get("languages"))),
        ]
        return " ".join(str(p).strip() for p in parts if p).strip()

    def _is_stem(self, text: str) -> bool:
        terms = (
            "computer", "science", "data", "engineering", "technology",
            "artificial intelligence", "software", "machine learning",
            "statistics", "mathematics",
        )
        return any(t in text.casefold() for t in terms)

    def _clamp(self, value: object) -> int:
        try:
            return max(0, min(100, int(value)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0
