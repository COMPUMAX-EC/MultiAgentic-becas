from __future__ import annotations


class DemoSchemaError(ValueError):
    pass


def build_workflow_step(
    step_name: object,
    status: object,
    count: object,
    message: object,
) -> dict:
    cleaned_name = _clean_text(step_name)
    if not cleaned_name:
        raise DemoSchemaError("step_name must be non-empty.")

    cleaned_status = _clean_text(status)
    if not cleaned_status:
        raise DemoSchemaError("status must be non-empty.")

    try:
        cleaned_count = int(count)
    except (TypeError, ValueError) as exc:
        raise DemoSchemaError("count must be numeric.") from exc

    return {
        "step_name": cleaned_name,
        "status": cleaned_status,
        "count": max(0, cleaned_count),
        "message": _clean_text(message) or "",
    }


def build_demo_output(
    demo_status: object,
    profile_summary: object,
    workflow_steps: object,
    generated_queries_count: object,
    sources_found_count: object,
    sources_validated_count: object,
    pages_read_count: object,
    scholarships_extracted_count: object,
    matches_count: object,
    ranked_results_count: object,
    top_recommendations: object,
    errors: object,
    output_files: object,
) -> dict:
    cleaned_status = _clean_text(demo_status)
    if not cleaned_status:
        raise DemoSchemaError("demo_status must be non-empty.")
    if not isinstance(workflow_steps, list):
        raise DemoSchemaError("workflow_steps must be a list.")
    if not isinstance(top_recommendations, list):
        raise DemoSchemaError("top_recommendations must be a list.")
    if not isinstance(errors, list):
        raise DemoSchemaError("errors must be a list.")
    if not isinstance(output_files, dict):
        raise DemoSchemaError("output_files must be a dictionary.")

    return {
        "demo_status": cleaned_status,
        "profile_summary": profile_summary if isinstance(profile_summary, dict) else {},
        "workflow_steps": workflow_steps,
        "generated_queries_count": _clean_count(generated_queries_count),
        "sources_found_count": _clean_count(sources_found_count),
        "sources_validated_count": _clean_count(sources_validated_count),
        "pages_read_count": _clean_count(pages_read_count),
        "scholarships_extracted_count": _clean_count(scholarships_extracted_count),
        "matches_count": _clean_count(matches_count),
        "ranked_results_count": _clean_count(ranked_results_count),
        "top_recommendations": top_recommendations,
        "errors": [str(error).strip() for error in errors if str(error).strip()],
        "output_files": {
            key: str(value).strip() for key, value in output_files.items() if str(value).strip()
        },
    }


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned_value = " ".join(value.strip().split())
    return cleaned_value or None


def _clean_count(value: object) -> int:
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        int_value = 0
    return max(0, int_value)
