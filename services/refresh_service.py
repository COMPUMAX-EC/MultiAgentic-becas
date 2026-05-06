from __future__ import annotations

from datetime import datetime, timezone

from config.settings import settings
from database.repository import (
    init_database,
    list_scholarships_for_refresh,
    update_scholarship_last_seen,
    update_scholarship_refresh_status,
)
from schemas.refresh_schema import build_refresh_result
from tools.date_validator import (
    detect_status_from_deadline,
    is_deadline_expired,
    normalize_deadline_value,
)
from tools.page_reader import PageReadError, read_page
from tools.text_cleaner import clean_text


class RefreshService:
    def __init__(self) -> None:
        self.summary = {
            "records_checked": 0,
            "kept_active": 0,
            "marked_closed": 0,
            "marked_expired": 0,
            "skipped_recent": 0,
            "skipped_closed": 0,
            "errors": [],
        }

    def refresh(self) -> dict:
        if not settings.REFRESH_ENABLED:
            return {
                "summary": {
                    **self.summary,
                    "errors": ["Refresh is disabled."],
                },
                "refresh_results": [],
            }

        init_database()
        rows = list_scholarships_for_refresh(
            limit=settings.REFRESH_MAX_RECORDS,
            stale_days=settings.REFRESH_STALE_DAYS,
            skip_closed=False,
        )

        refresh_results: list[dict] = []
        for row in rows:
            result = self._refresh_row(row)
            refresh_results.append(result)

        return {
            "summary": self.summary,
            "refresh_results": refresh_results,
        }

    def _refresh_row(self, row: dict) -> dict:
        self.summary["records_checked"] += 1
        scholarship_hash = row.get("scholarship_hash")
        previous_status = str(row.get("application_status") or "unknown")
        previous_deadline = normalize_deadline_value(row.get("deadline"))
        refreshed_at = datetime.now(timezone.utc).isoformat()
        reasons: list[str] = []

        try:
            if not bool(row.get("is_stale", True)):
                self.summary["skipped_recent"] += 1
                return build_refresh_result(
                    scholarship_name=row.get("scholarship_name"),
                    source_url=row.get("source_url"),
                    previous_status=previous_status,
                    current_status=previous_status,
                    previous_deadline=previous_deadline,
                    current_deadline=previous_deadline,
                    action="skipped_recent",
                    reasons=["Record was refreshed recently and is skipped for now."],
                    refreshed_at=refreshed_at,
                )

            if settings.REFRESH_SKIP_CLOSED and previous_status.strip().lower() == "closed":
                self.summary["skipped_closed"] += 1
                update_scholarship_last_seen(scholarship_hash)
                reasons.append("Closed scholarship was skipped by refresh policy.")
                return build_refresh_result(
                    scholarship_name=row.get("scholarship_name"),
                    source_url=row.get("source_url"),
                    previous_status=previous_status,
                    current_status=previous_status,
                    previous_deadline=previous_deadline,
                    current_deadline=previous_deadline,
                    action="skipped_closed",
                    reasons=reasons,
                    refreshed_at=refreshed_at,
                )

            current_deadline = previous_deadline
            current_status = previous_status.strip().lower() or "unknown"

            if settings.REFRESH_CHECK_PAGES:
                current_deadline, page_reason = self._check_page_for_deadline(row)
                if page_reason:
                    reasons.append(page_reason)
                current_status = detect_status_from_deadline(
                    current_deadline, current_status
                )
            else:
                current_status = detect_status_from_deadline(
                    current_deadline, current_status
                )

            if current_status == "closed":
                self.summary["marked_closed"] += 1
                update_scholarship_refresh_status(
                    scholarship_hash,
                    application_status="closed",
                    deadline=current_deadline,
                )
                reasons.append("Application status is clearly closed.")
                action = "marked_closed"
            elif current_status == "expired" or is_deadline_expired(current_deadline):
                self.summary["marked_expired"] += 1
                update_scholarship_refresh_status(
                    scholarship_hash,
                    application_status="closed",
                    deadline=current_deadline,
                )
                reasons.append("Deadline is clearly before the current date.")
                current_status = "expired"
                action = "marked_expired"
            elif current_status in {"open", "upcoming"}:
                self.summary["kept_active"] += 1
                update_scholarship_last_seen(scholarship_hash)
                reasons.append("Record remains active after deterministic refresh checks.")
                action = "kept_active"
            else:
                self.summary["kept_active"] += 1
                update_scholarship_refresh_status(
                    scholarship_hash,
                    application_status="unknown",
                    deadline=current_deadline,
                )
                reasons.append("Deadline or status is unclear after refresh checks.")
                action = "marked_unknown"

            return build_refresh_result(
                scholarship_name=row.get("scholarship_name"),
                source_url=row.get("source_url"),
                previous_status=previous_status,
                current_status=current_status,
                previous_deadline=previous_deadline,
                current_deadline=current_deadline,
                action=action,
                reasons=reasons,
                refreshed_at=refreshed_at,
            )
        except Exception as exc:
            self.summary["errors"].append(str(exc))
            return build_refresh_result(
                scholarship_name=row.get("scholarship_name"),
                source_url=row.get("source_url"),
                previous_status=previous_status,
                current_status=previous_status,
                previous_deadline=previous_deadline,
                current_deadline=previous_deadline,
                action="update_failed",
                reasons=reasons,
                refreshed_at=refreshed_at,
                error=str(exc),
            )

    def _check_page_for_deadline(self, row: dict) -> tuple[str | None, str | None]:
        source_url = str(row.get("source_url") or "").strip()
        if not source_url:
            return normalize_deadline_value(row.get("deadline")), None

        try:
            raw_content = read_page(source_url)
            cleaned_text = clean_text(raw_content, max_chars=4000).casefold()
            if "applications closed" in cleaned_text or "application closed" in cleaned_text:
                return normalize_deadline_value(row.get("deadline")), "Source page indicates applications are closed."
        except PageReadError as exc:
            return normalize_deadline_value(row.get("deadline")), f"Page check failed: {exc}"

        return normalize_deadline_value(row.get("deadline")), None
