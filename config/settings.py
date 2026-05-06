from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    PROJECT_ROOT: Path
    DATA_DIR: Path
    PROFILES_DIR: Path
    RESULTS_DIR: Path
    CACHE_DIR: Path
    DEFAULT_PROFILE_PATH: Path
    LLM_PROVIDER: str
    OLLAMA_MODEL: str
    OLLAMA_HOST: str
    LLM_TIMEOUT_SECONDS: int
    SEARCH_PROVIDER: str
    SEARCH_MAX_RESULTS_PER_QUERY: int
    SEARCH_TIMEOUT_SECONDS: int
    SEARCH_CACHE_ENABLED: bool
    SOURCE_VALIDATION_USE_LLM: bool
    SOURCE_VALIDATION_MIN_RELIABILITY: int
    SOURCE_VALIDATION_MIN_RELEVANCE: int
    PAGE_READ_TIMEOUT_SECONDS: int
    PAGE_MAX_CHARS: int
    PAGE_CACHE_ENABLED: bool
    PAGE_ALLOWED_DECISIONS: tuple[str, ...]
    EXTRACTION_MAX_PAGES: int
    EXTRACTION_MIN_CONFIDENCE: int
    EXTRACTION_TEXT_MAX_CHARS: int
    DATABASE_PATH: Path
    KNOWLEDGE_BASE_ENABLED: bool
    SCHOLARSHIP_DEDUP_STRATEGY: str
    MATCHING_USE_LLM: bool
    MATCHING_MIN_COMPATIBILITY_SCORE: int
    MATCHING_LANGUAGE_STRICTNESS: str
    MATCHING_SCORE_VERSION: str
    RETRIEVAL_ENABLED: bool
    RETRIEVAL_MAX_RESULTS: int
    RETRIEVAL_MIN_SCORE: int
    RETRIEVAL_MODE: str
    REFRESH_ENABLED: bool
    REFRESH_MAX_RECORDS: int
    REFRESH_STALE_DAYS: int
    REFRESH_CHECK_PAGES: bool
    REFRESH_SKIP_CLOSED: bool
    RANKING_MIN_FINAL_SCORE: int
    RANKING_MAX_RESULTS: int
    RANKING_SCORE_VERSION: str
    DEFAULT_OUTPUT_FORMAT: str = "json"


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

settings = Settings(
    PROJECT_ROOT=PROJECT_ROOT,
    DATA_DIR=DATA_DIR,
    PROFILES_DIR=DATA_DIR / "profiles",
    RESULTS_DIR=DATA_DIR / "results",
    CACHE_DIR=DATA_DIR / "cache",
    DEFAULT_PROFILE_PATH=DATA_DIR / "profiles" / "sample_profile.json",
    LLM_PROVIDER=os.getenv("LLM_PROVIDER", "ollama"),
    OLLAMA_MODEL=os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
    OLLAMA_HOST=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    LLM_TIMEOUT_SECONDS=int(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
    SEARCH_PROVIDER=os.getenv("SEARCH_PROVIDER", "duckduckgo"),
    SEARCH_MAX_RESULTS_PER_QUERY=int(os.getenv("SEARCH_MAX_RESULTS_PER_QUERY", "5")),
    SEARCH_TIMEOUT_SECONDS=int(os.getenv("SEARCH_TIMEOUT_SECONDS", "20")),
    SEARCH_CACHE_ENABLED=os.getenv("SEARCH_CACHE_ENABLED", "true").strip().lower()
    == "true",
    SOURCE_VALIDATION_USE_LLM=os.getenv(
        "SOURCE_VALIDATION_USE_LLM", "false"
    ).strip().lower()
    == "true",
    SOURCE_VALIDATION_MIN_RELIABILITY=int(
        os.getenv("SOURCE_VALIDATION_MIN_RELIABILITY", "50")
    ),
    SOURCE_VALIDATION_MIN_RELEVANCE=int(
        os.getenv("SOURCE_VALIDATION_MIN_RELEVANCE", "50")
    ),
    PAGE_READ_TIMEOUT_SECONDS=int(os.getenv("PAGE_READ_TIMEOUT_SECONDS", "25")),
    PAGE_MAX_CHARS=int(os.getenv("PAGE_MAX_CHARS", "12000")),
    PAGE_CACHE_ENABLED=os.getenv("PAGE_CACHE_ENABLED", "true").strip().lower()
    == "true",
    PAGE_ALLOWED_DECISIONS=tuple(
        decision.strip()
        for decision in os.getenv("PAGE_ALLOWED_DECISIONS", "accept,review").split(",")
        if decision.strip()
    ),
    EXTRACTION_MAX_PAGES=int(os.getenv("EXTRACTION_MAX_PAGES", "10")),
    EXTRACTION_MIN_CONFIDENCE=int(os.getenv("EXTRACTION_MIN_CONFIDENCE", "50")),
    EXTRACTION_TEXT_MAX_CHARS=int(os.getenv("EXTRACTION_TEXT_MAX_CHARS", "12000")),
    DATABASE_PATH=Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "scholarships.db"))),
    KNOWLEDGE_BASE_ENABLED=os.getenv("KNOWLEDGE_BASE_ENABLED", "true").strip().lower()
    == "true",
    SCHOLARSHIP_DEDUP_STRATEGY=os.getenv(
        "SCHOLARSHIP_DEDUP_STRATEGY", "source_url_and_name"
    ),
    MATCHING_USE_LLM=os.getenv("MATCHING_USE_LLM", "false").strip().lower()
    == "true",
    MATCHING_MIN_COMPATIBILITY_SCORE=int(
        os.getenv("MATCHING_MIN_COMPATIBILITY_SCORE", "50")
    ),
    MATCHING_LANGUAGE_STRICTNESS=os.getenv(
        "MATCHING_LANGUAGE_STRICTNESS", "moderate"
    ).strip().lower(),
    MATCHING_SCORE_VERSION=os.getenv("MATCHING_SCORE_VERSION", "v1").strip(),
    RETRIEVAL_ENABLED=os.getenv("RETRIEVAL_ENABLED", "true").strip().lower()
    == "true",
    RETRIEVAL_MAX_RESULTS=int(os.getenv("RETRIEVAL_MAX_RESULTS", "10")),
    RETRIEVAL_MIN_SCORE=int(os.getenv("RETRIEVAL_MIN_SCORE", "40")),
    RETRIEVAL_MODE=os.getenv("RETRIEVAL_MODE", "keyword").strip().lower(),
    REFRESH_ENABLED=os.getenv("REFRESH_ENABLED", "true").strip().lower() == "true",
    REFRESH_MAX_RECORDS=int(os.getenv("REFRESH_MAX_RECORDS", "20")),
    REFRESH_STALE_DAYS=int(os.getenv("REFRESH_STALE_DAYS", "7")),
    REFRESH_CHECK_PAGES=os.getenv("REFRESH_CHECK_PAGES", "false").strip().lower()
    == "true",
    REFRESH_SKIP_CLOSED=os.getenv("REFRESH_SKIP_CLOSED", "true").strip().lower()
    == "true",
    RANKING_MIN_FINAL_SCORE=int(os.getenv("RANKING_MIN_FINAL_SCORE", "50")),
    RANKING_MAX_RESULTS=int(os.getenv("RANKING_MAX_RESULTS", "10")),
    RANKING_SCORE_VERSION=os.getenv("RANKING_SCORE_VERSION", "v1").strip(),
)
