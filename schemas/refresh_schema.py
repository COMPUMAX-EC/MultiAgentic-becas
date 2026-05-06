from __future__ import annotations


ALLOWED_REFRESH_ACTIONS = {
    "kept_active",
    "marked_closed",
    "marked_expired",
    "marked_unknown",
    "skipped_recent",
    "skipped_closed",
    "update_failed",
}


class RefreshValidationError(ValueError):
    pass


def build_refresh_result(
    scholarship_name: object,
    source_url: object,
    previous_status: object,
    current_status: object,
    previous_deadline: object,
    current_deadline: object,
    action: object,
    reasons: object,
    refreshed_at: object,
    error: object = None,
) -> dict:
    cleaned_name = _clean_text(scholarship_name)
    if not cleaned_name:
        raise RefreshValidationError("scholarship_name must be non-empty.")

    cleaned_source_url = _clean_text(source_url)
    if not cleaned_source_url:
        raise RefreshValidationError("source_url must be non-empty.")

    cleaned_action = _clean_text(action)
    if cleaned_action not in ALLOWED_REFRESH_ACTIONS:
        raise RefreshValidationError(f"Unsupported action: {action}")

    return {
        "scholarship_name": cleaned_name,
        "source_url": cleaned_source_url,
        "previous_status": _clean_text(previous_status) or "unknown",
        "current_status": _clean_text(current_status) or "unknown",
        "previous_deadline": _clean_text(previous_deadline),
        "current_deadline": _clean_text(current_deadline),
        "action": cleaned_action,
        "reasons": _clean_list(reasons),
        "refreshed_at": _clean_text(refreshed_at) or "",
        "error": _clean_text(error),
    }


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned_value = " ".join(value.strip().split())
    return cleaned_value or None


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned_values: list[str] = []
    for item in value:
        cleaned_item = _clean_text(item)
        if cleaned_item:
            cleaned_values.append(cleaned_item)
    return cleaned_values
