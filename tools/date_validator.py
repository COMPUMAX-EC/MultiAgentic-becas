from __future__ import annotations

from datetime import datetime, timezone


EXPIRED_SIGNAL_TERMS = (
    "expired",
    "closed",
    "deadline passed",
    "applications closed",
    "application closed",
    "no longer accepting",
    "past deadline",
)

OLD_ACTIVE_CYCLE_TERMS = (
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
)

CYCLE_CONTEXT_TERMS = (
    "scholarship",
    "application",
    "deadline",
    "cycle",
    "intake",
    "call",
)

DEADLINE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
)


def has_obvious_expired_signal(title: str, snippet: str) -> bool:
    text = f"{title} {snippet}".casefold()

    if any(term in text for term in EXPIRED_SIGNAL_TERMS):
        return True

    return any(year in text for year in OLD_ACTIVE_CYCLE_TERMS) and any(
        term in text for term in CYCLE_CONTEXT_TERMS
    )


def normalize_deadline_value(deadline: object) -> str | None:
    if not isinstance(deadline, str):
        return None
    cleaned_deadline = " ".join(deadline.strip().split())
    return cleaned_deadline or None


def is_deadline_expired(deadline: object) -> bool:
    normalized_deadline = normalize_deadline_value(deadline)
    if not normalized_deadline:
        return False

    for deadline_format in DEADLINE_FORMATS:
        try:
            parsed_deadline = datetime.strptime(
                normalized_deadline, deadline_format
            ).date()
            return parsed_deadline < datetime.now(timezone.utc).date()
        except ValueError:
            continue

    if normalized_deadline.isdigit() and len(normalized_deadline) == 4:
        try:
            return int(normalized_deadline) < datetime.now(timezone.utc).year
        except ValueError:
            return False

    return False


def detect_status_from_deadline(
    deadline: object, application_status: object
) -> str:
    normalized_status = (
        str(application_status).strip().lower() if application_status is not None else ""
    )
    if normalized_status == "closed":
        return "closed"
    if is_deadline_expired(deadline):
        return "expired"
    if normalized_status in {"open", "upcoming", "unknown"}:
        return normalized_status
    return "unknown"
