"""agent_status.py — Infers per-agent status from the latest results file."""
from __future__ import annotations
import re, time
from dataclasses import dataclass, field
from pathlib import Path

AGENT_REGISTRY = [
    {"id": "profile_agent",          "label": "Profile Agent",          "phase": "Phase 3",  "icon": "👤"},
    {"id": "query_agent",            "label": "Query Agent",            "phase": "Phase 4",  "icon": "🔍"},
    {"id": "search_agent",           "label": "Search Agent",           "phase": "Phase 5",  "icon": "🌐"},
    {"id": "source_validator_agent", "label": "Source Validator Agent", "phase": "Phase 6",  "icon": "✅"},
    {"id": "page_reader_agent",      "label": "Page Reader Agent",      "phase": "Phase 7",  "icon": "📄"},
    {"id": "extraction_agent",       "label": "Extraction Agent",       "phase": "Phase 8",  "icon": "⚙️"},
    {"id": "matching_agent",         "label": "Matching Agent",         "phase": "Phase 11", "icon": "🎯"},
    {"id": "ranking_agent",          "label": "Ranking Agent",          "phase": "Phase 12", "icon": "🏆"},
]

_KEYWORD_MAP = {
    "profile": "profile_agent", "ProfileAgent": "profile_agent",
    "query": "query_agent",     "QueryAgent": "query_agent",
    "web search": "search_agent", "SearchAgent": "search_agent",
    "source": "source_validator_agent", "SourceValidator": "source_validator_agent",
    "page": "page_reader_agent",  "PageReader": "page_reader_agent",
    "extract": "extraction_agent", "ExtractionAgent": "extraction_agent",
    "match": "matching_agent",    "MatchingAgent": "matching_agent",
    "rank": "ranking_agent",      "RankingAgent": "ranking_agent",
}


@dataclass
class AgentStatus:
    id: str
    label: str
    phase: str
    icon: str
    status: str = "idle"
    last_message: str = ""
    last_seen: str = ""
    log_lines: list[str] = field(default_factory=list)


def get_agent_statuses(results_dir: Path | str | None = None) -> list[AgentStatus]:
    if results_dir is None:
        results_dir = Path(__file__).resolve().parents[2] / "data" / "results"
    results_dir = Path(results_dir)

    statuses = {e["id"]: AgentStatus(**{k: e[k] for k in ("id","label","phase","icon")})
                for e in AGENT_REGISTRY}

    log_files = list(results_dir.glob("*.log")) + list(results_dir.glob("*.json"))
    if not log_files:
        return list(statuses.values())

    log_path = max(log_files, key=lambda p: p.stat().st_mtime)
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
    except Exception:
        return list(statuses.values())

    active: set[str] = set()
    for line in lines:
        ll = line.lower()
        for kw, aid in _KEYWORD_MAP.items():
            if kw.lower() in ll:
                a = statuses[aid]
                active.add(aid)
                a.log_lines.append(line.strip())
                a.last_message = line.strip()[-120:]
                ts = re.search(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", line)
                if ts:
                    a.last_seen = ts.group()
        if any(w in ll for w in ("error", "exception", "failed")):
            for aid in active:
                statuses[aid].status = "error"

    order = [e["id"] for e in AGENT_REGISTRY]
    last_active_idx = max((i for i, aid in enumerate(order) if aid in active), default=-1)
    mtime = log_path.stat().st_mtime
    for idx, aid in enumerate(order):
        a = statuses[aid]
        if a.status == "error":
            continue
        if aid not in active:
            a.status = "idle"
        elif idx < last_active_idx:
            a.status = "done"
        else:
            a.status = "running" if time.time() - mtime < 60 else "done"

    return list(statuses.values())
