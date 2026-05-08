from __future__ import annotations

import json
import hashlib
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from agent.extraction_agent import ExtractionAgent
from agent.page_reader_agent import PageReaderAgent
from agent.profile_agent import ProfileAgent
from agent.query_agent import QueryAgent
from agent.search_agent import SearchAgent
from agent.source_validator_agent import SourceValidatorAgent
from config.settings import settings
from services.matching_service import run_matching
from services.ranking_service import run_ranking
from tools.date_validator import detect_status_from_deadline, has_obvious_expired_signal
from utils.profile_normalization import complete_profile_defaults, infer_profile_from_text
from utils.url_utils import first_useful_url, normalize_useful_url


app = FastAPI(title="Scholarship Search Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


PROFILE_AGENT = ProfileAgent()
QUERY_AGENT = QueryAgent()
SEARCH_AGENT = SearchAgent()
SOURCE_VALIDATOR_AGENT = SourceValidatorAgent()
PAGE_READER_AGENT = PageReaderAgent()
EXTRACTION_AGENT = ExtractionAgent()
RECOMMENDED_LABELS = {
    "high_priority",
    "medium_priority",
    "possible_match",
    "strong_match",
}
LESS_RECOMMENDED_LABELS = {
    "low_priority",
    "not_recommended",
    "insufficient_information",
    "rejected",
    "weak_match",
    "not_eligible",
}
LESS_RECOMMENDED_DISPLAY_LIMIT = 10
REQUIRED_SEARCH_STEP_NAMES = (
    "Reading profile input",
    "Normalizing profile",
    "Generating global scholarship search queries",
    "Searching global scholarship sources",
    "Validating official and verified sources",
    "Reading scholarship pages",
    "Extracting scholarship data",
    "Matching scholarships with profile",
    "Ranking recommendations",
    "Preparing final results",
)
SOURCE_POLICY_ALLOWED_TYPES = {
    "university",
    "institute",
    "institution",
    "government",
    "organization",
    "foundation",
    "company",
    "international_organization",
    "official_pdf",
    "verified_news",
    "verified_newspaper",
    "verified_magazine",
    "verified_education_portal",
    "verified_scholarship_information_source",
    "official_university",
    "official_institute",
    "official_institution",
    "official_government",
    "official_organization",
    "official_foundation",
    "official_company",
    "official_pdf",
    "official_announcement",
    "verified_news",
    "trusted_portal",
}


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Scholarship Search Agent API",
        "available_endpoints": ["/health", "/demo/latest", "/search", "/docs"],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Scholarship Search Agent API",
    }


@app.get("/demo/latest")
def get_latest_demo():
    latest_demo = load_latest_demo_payload()
    if latest_demo is None:
        return build_empty_response(
            message="No demo results found. Run python main.py --demo first."
        )

    return normalize_frontend_response(
        latest_demo,
        status_override=normalize_status(latest_demo.get("demo_status"), default="ok"),
        message="Latest demo recommendations loaded.",
    )


@app.post("/search")
async def search_scholarships(request: Request):
    parsed_request = await parse_search_request(request)
    workflow_steps = [
        build_workflow_step(
            "Reading profile input",
            "completed",
            1,
            "Profile input received.",
        )
    ]

    if parsed_request["pdf_filename"]:
        workflow_steps.append(
            build_workflow_step(
                "Reading uploaded CV PDF",
                "skipped",
                1,
                "PDF received but parsing is not connected yet.",
            )
        )

    try:
        normalized_profile = prepare_search_profile(
            parsed_request["received_profile"],
            parsed_request["raw_profile_text"],
            parsed_request["scholarship_goal"],
        )
        search_signature = build_search_signature(normalized_profile)
        workflow_steps.append(
            build_workflow_step(
                "Normalizing profile",
                "completed",
                1,
                "Profile input received and normalized.",
            )
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Profile could not be normalized: {exc}",
        ) from exc

    pipeline_payload = run_live_search_pipeline(normalized_profile, workflow_steps)
    response = normalize_frontend_response(
        pipeline_payload,
        status_override=pipeline_payload["status"],
        message=pipeline_payload["message"],
        extra_workflow_steps=pipeline_payload["workflow_steps"],
    )
    response["normalized_profile"] = normalized_profile
    response["input_type"] = parsed_request["input_type"]
    response["raw_profile_text"] = parsed_request["raw_profile_text"]
    response["pdf_filename"] = parsed_request["pdf_filename"]
    response["search_signature"] = search_signature
    response["filtering_layers"] = build_filtering_layers(normalized_profile)
    response["metrics"] = normalize_metrics(pipeline_payload.get("metrics"))
    response["rejection_summary"] = normalize_rejection_summary(
        pipeline_payload.get("rejection_summary")
    )
    response["workflow_counts"] = response["metrics"]
    ensure_response_display_links(response)
    return response


async def parse_search_request(request: Request):
    content_type = request.headers.get("content-type", "")
    content_type_lower = content_type.lower()

    if "multipart/form-data" in content_type_lower:
        return await parse_multipart_search_request(request, content_type)

    return await parse_json_search_request(request)


async def parse_json_search_request(request: Request):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Request body must be valid JSON or multipart/form-data.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="JSON request body must be an object.",
        )

    profile = payload.get("profile")
    raw_profile_text = normalize_optional_text(payload.get("raw_profile_text"))
    scholarship_goal = normalize_optional_text(payload.get("scholarship_goal"))

    if isinstance(profile, dict) and profile:
        return {
            "input_type": "structured_profile",
            "received_profile": profile,
            "raw_profile_text": raw_profile_text,
            "scholarship_goal": scholarship_goal,
            "pdf_filename": None,
        }

    if raw_profile_text:
        return {
            "input_type": "raw_text",
            "received_profile": None,
            "raw_profile_text": raw_profile_text,
            "scholarship_goal": scholarship_goal,
            "pdf_filename": None,
        }

    raise HTTPException(
        status_code=400,
        detail="Provide either a non-empty profile object or raw_profile_text.",
    )


async def parse_multipart_search_request(request: Request, content_type: str):
    try:
        body = await request.body()
        form, files = parse_multipart_body(body, content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Multipart form data could not be read.",
        ) from exc

    raw_profile_text = normalize_optional_text(form.get("raw_profile_text"))
    scholarship_goal = normalize_optional_text(form.get("scholarship_goal"))
    pdf_filename = files.get("cv_pdf")

    if not raw_profile_text:
        raise HTTPException(
            status_code=400,
            detail="Multipart requests must include raw_profile_text.",
        )

    return {
        "input_type": "multipart",
        "received_profile": None,
        "raw_profile_text": raw_profile_text,
        "scholarship_goal": scholarship_goal,
        "pdf_filename": pdf_filename,
    }


def prepare_search_profile(
    received_profile: dict | None,
    raw_profile_text: str,
    scholarship_goal: str,
):
    if received_profile:
        completed_profile = complete_profile_defaults(received_profile)
    else:
        completed_profile = infer_profile_from_text(raw_profile_text, scholarship_goal)

    return PROFILE_AGENT.prepare_profile(completed_profile)


def run_live_search_pipeline(
    normalized_profile: dict,
    workflow_steps: list[dict],
) -> dict:
    errors: list[str] = []
    queries: list[dict] = []
    candidate_results: list[dict] = []
    validated_sources: list[dict] = []
    accepted_sources: list[dict] = []
    page_results: list[dict] = []
    scholarships: list[dict] = []
    active_scholarships: list[dict] = []
    link_ready_scholarships: list[dict] = []
    matching_results: list[dict] = []
    ranked_results: list[dict] = []
    metrics = build_empty_metrics()
    rejection_summary = build_empty_rejection_summary()

    try:
        queries = QUERY_AGENT.generate_queries(normalized_profile)
        metrics["generated_queries_count"] = len(queries)
        workflow_steps.append(
            build_workflow_step(
                "Generating global scholarship search queries",
                "completed",
                len(queries),
                f"Generated {len(queries)} profile-dependent search queries.",
            )
        )
    except Exception as exc:
        return build_failed_pipeline_payload(
            workflow_steps,
            "Generating global scholarship search queries",
            f"Live query generation failed: {exc}",
            errors,
        )

    try:
        candidate_results = SEARCH_AGENT.search(queries)
        raw_sources_count = int(
            getattr(SEARCH_AGENT, "last_raw_results_count", len(candidate_results)) or 0
        )
        deduplicated_sources_count = int(
            getattr(SEARCH_AGENT, "last_deduplicated_count", len(candidate_results)) or 0
        )
        metrics["sources_found_count"] = raw_sources_count
        metrics["sources_deduplicated_count"] = deduplicated_sources_count
        rejection_summary["duplicate"] += max(
            0,
            raw_sources_count - deduplicated_sources_count,
        )
        workflow_steps.append(
            build_workflow_step(
                "Searching global scholarship sources",
                "completed",
                deduplicated_sources_count,
                (
                    f"Collected {raw_sources_count} raw candidates and kept "
                    f"{deduplicated_sources_count} deduplicated sources."
                ),
            )
        )
    except Exception as exc:
        return build_failed_pipeline_payload(
            workflow_steps,
            "Searching global scholarship sources",
            f"Live web search failed: {exc}",
            errors,
        )

    try:
        validated_sources = SOURCE_VALIDATOR_AGENT.validate_sources(candidate_results)
        accepted_sources = filter_policy_accepted_sources(validated_sources)
        source_counts = count_source_acceptance_statuses(validated_sources, accepted_sources)
        source_rejections = summarize_source_rejections(validated_sources)
        merge_rejection_summary(rejection_summary, source_rejections)
        metrics["sources_accepted_count"] = source_counts["accepted"]
        metrics["sources_accepted_with_warning_count"] = source_counts[
            "accepted_with_warning"
        ]
        metrics["sources_rejected_count"] = source_counts["rejected"]
        workflow_steps.append(
            build_workflow_step(
                "Validating official and verified sources",
                "completed",
                len(accepted_sources),
                (
                    f"Accepted {source_counts['accepted']} sources and "
                    f"{source_counts['accepted_with_warning']} sources with warnings "
                    f"from {len(validated_sources)} validated candidates. "
                    f"Rejected {source_counts['rejected']} sources."
                ),
            )
        )
    except Exception as exc:
        return build_failed_pipeline_payload(
            workflow_steps,
            "Validating official and verified sources",
            f"Source validation failed: {exc}",
            errors,
        )

    try:
        page_results = PAGE_READER_AGENT.read_pages(accepted_sources)
        page_results = enrich_page_results_with_source_metadata(
            page_results,
            accepted_sources,
        )
        readable_page_count = count_readable_pages(page_results)
        failed_page_count = count_failed_pages(page_results)
        metrics["pages_read_count"] = readable_page_count
        metrics["pages_failed_count"] = failed_page_count
        rejection_summary["read_failed"] += failed_page_count
        workflow_steps.append(
            build_workflow_step(
                "Reading scholarship pages",
                "completed",
                readable_page_count,
                (
                    f"Read {readable_page_count} scholarship pages and failed "
                    f"to read {failed_page_count} accepted sources."
                ),
            )
        )
    except Exception as exc:
        return build_failed_pipeline_payload(
            workflow_steps,
            "Reading scholarship pages",
            f"Page reading failed: {exc}",
            errors,
        )

    try:
        scholarships = EXTRACTION_AGENT.extract_scholarships(page_results)
        active_scholarships = filter_active_scholarships(scholarships)
        active_with_link_count = count_scholarships_with_useful_link(active_scholarships)
        link_ready_scholarships = prepare_scholarships_for_matching(active_scholarships)
        expired_count = len(scholarships) - len(active_scholarships)
        no_link_count = max(0, len(active_scholarships) - active_with_link_count)
        link_duplicate_count = max(0, active_with_link_count - len(link_ready_scholarships))
        metrics["scholarships_extracted_count"] = len(scholarships)
        metrics["expired_rejected_count"] = expired_count
        metrics["scholarships_with_useful_link_count"] = len(
            link_ready_scholarships
        )
        rejection_summary["expired_or_closed"] += expired_count
        rejection_summary["no_useful_link"] += no_link_count
        rejection_summary["duplicate"] += link_duplicate_count
        rejection_summary["extraction_failed"] += len(EXTRACTION_AGENT.extraction_errors)
        errors.extend(
            normalize_pipeline_errors(
                "Extraction",
                EXTRACTION_AGENT.extraction_errors,
            )
        )
        workflow_steps.append(
            build_workflow_step(
                "Extracting scholarship data",
                "completed",
                len(scholarships),
                (
                    f"Extracted {len(scholarships)} scholarship records and kept "
                    f"{len(link_ready_scholarships)} active records with useful links."
                    + (
                        f" Filtered {expired_count} expired or closed records."
                        if expired_count
                        else ""
                    )
                ),
            )
        )
    except Exception as exc:
        return build_failed_pipeline_payload(
            workflow_steps,
            "Extracting scholarship data",
            f"Scholarship extraction failed: {exc}",
            errors,
        )

    try:
        matching_payload = run_matching(normalized_profile, link_ready_scholarships)
        matching_results = matching_payload["matching_results"]
        matching_summary = matching_payload["summary"]
        metrics["matched_count"] = len(matching_results)
        errors.extend(
            normalize_pipeline_errors("Matching", matching_summary.get("errors", []))
        )
        workflow_steps.append(
            build_workflow_step(
                "Matching scholarships with profile",
                "completed",
                len(matching_results),
                f"Matched {len(matching_results)} scholarships against the profile.",
            )
        )
    except Exception as exc:
        return build_failed_pipeline_payload(
            workflow_steps,
            "Matching scholarships with profile",
            f"Scholarship matching failed: {exc}",
            errors,
        )

    try:
        ranking_payload = run_ranking(matching_results)
        ranked_results = filter_ranked_results_with_links(ranking_payload["ranked_results"])
        ranking_summary = ranking_payload["summary"]
        metrics["ranked_count"] = len(ranked_results)
        recommended_results, less_recommended_results = split_recommendations(
            normalize_recommendation_list(ranked_results)
        )
        metrics["recommended_count"] = len(recommended_results)
        metrics["less_recommended_count"] = len(less_recommended_results)
        errors.extend(
            normalize_pipeline_errors("Ranking", ranking_summary.get("errors", []))
        )
        workflow_steps.append(
            build_workflow_step(
                "Ranking recommendations",
                "completed",
                len(ranked_results),
                f"Ranked {len(ranked_results)} scholarship recommendations.",
            )
        )
    except Exception as exc:
        return build_failed_pipeline_payload(
            workflow_steps,
            "Ranking recommendations",
            f"Scholarship ranking failed: {exc}",
            errors,
        )

    status = "ok"
    message = "Live scholarship search completed."
    if not ranked_results:
        status = "failed"
        message = "No live recommendations were returned for this profile."
        errors.append(
            "Live search completed without readable scholarship recommendations for this profile."
        )
    elif errors:
        status = "partial_failure"
        message = "Live scholarship search completed with partial errors."

    workflow_steps.append(
        build_workflow_step(
            "Preparing final results",
            "completed" if ranked_results else "failed",
            len(ranked_results),
            (
                f"Prepared {len(ranked_results)} final profile-dependent results."
                if ranked_results
                else "No final recommendations were available for this profile."
            ),
        )
    )

    return {
        "status": status,
        "message": message,
        "workflow_steps": ensure_required_workflow_steps(workflow_steps),
        "ranked_results": ranked_results,
        "recommended": [],
        "less_recommended": [],
        "errors": dedupe_text_values(errors),
        "metrics": metrics,
        "rejection_summary": rejection_summary,
        "workflow_counts": metrics,
    }


def build_failed_pipeline_payload(
    workflow_steps: list[dict],
    failed_step_name: str,
    message: str,
    errors: list[str],
) -> dict:
    workflow_steps.append(
        build_workflow_step(
            failed_step_name,
            "failed",
            0,
            message,
        )
    )
    errors.append(message)
    workflow_steps.append(
        build_workflow_step(
            "Preparing final results",
            "failed",
            0,
            "Live search stopped before final recommendations could be prepared.",
        )
    )
    return {
        "status": "failed",
        "message": message,
        "workflow_steps": ensure_required_workflow_steps(workflow_steps),
        "ranked_results": [],
        "recommended": [],
        "less_recommended": [],
        "errors": dedupe_text_values(errors),
        "metrics": build_empty_metrics(),
        "rejection_summary": build_empty_rejection_summary(),
        "workflow_counts": build_empty_metrics(),
    }


def ensure_response_display_links(response: dict) -> None:
    for key in (
        "ranked_results",
        "recommended",
        "less_recommended",
        "top_recommendations",
        "recommendations",
        "results",
    ):
        records = response.get(key)
        if not isinstance(records, list):
            continue
        link_ready_records = []
        for record in records:
            if isinstance(record, dict):
                normalized_record = normalize_link_fields(record)
                if normalized_record["display_link"]:
                    link_ready_records.append(normalized_record)
        response[key] = link_ready_records


def filter_policy_accepted_sources(validated_sources: list[dict]) -> list[dict]:
    return [
        source for source in validated_sources if is_policy_accepted_source(source)
    ]


def count_source_acceptance_statuses(
    validated_sources: list[dict],
    accepted_sources: list[dict],
) -> dict[str, int]:
    accepted_urls = {source.get("url") for source in accepted_sources}
    accepted = 0
    accepted_with_warning = 0
    for source in accepted_sources:
        if source.get("acceptance_status") == "accepted_with_warning" or source.get(
            "decision"
        ) == "review":
            accepted_with_warning += 1
        else:
            accepted += 1

    return {
        "accepted": accepted,
        "accepted_with_warning": accepted_with_warning,
        "rejected": len(
            [source for source in validated_sources if source.get("url") not in accepted_urls]
        ),
    }


def is_policy_accepted_source(source: dict) -> bool:
    if source.get("decision") not in {"accept", "review"}:
        return False

    source_type = normalize_optional_text(source.get("source_type"))
    if source_type not in SOURCE_POLICY_ALLOWED_TYPES:
        return False

    risk_flags = {
        normalize_optional_text(flag).lower()
        for flag in source.get("risk_flags", []) or []
        if normalize_optional_text(flag)
    }
    if "expired_or_closed" in risk_flags or "blog_or_media_domain" in risk_flags:
        return False

    return True


def enrich_page_results_with_source_metadata(
    page_results: list[dict],
    validated_sources: list[dict],
) -> list[dict]:
    sources_by_url = {
        first_useful_url(source.get("url"), source.get("source_url")): source
        for source in validated_sources
    }
    enriched_page_results: list[dict] = []

    for page_result in page_results:
        source = sources_by_url.get(
            first_useful_url(page_result.get("url"), page_result.get("source_url")),
            {},
        )
        enriched_page_result = dict(page_result)
        enriched_page_result["source_url"] = first_useful_url(
            page_result.get("source_url"),
            source.get("source_url"),
            source.get("url"),
        )
        enriched_page_result["original_url"] = first_useful_url(
            page_result.get("original_url"),
            source.get("original_url"),
            enriched_page_result["source_url"],
        )
        enriched_page_result["query_used"] = page_result.get("query_used") or source.get(
            "query_used",
            "",
        )
        enriched_page_result["source_type"] = page_result.get("source_type") or source.get(
            "source_type",
            "",
        )
        enriched_page_result["source_reliability_score"] = source.get(
            "reliability_score"
        )
        enriched_page_result["source_acceptance_status"] = source.get(
            "acceptance_status"
        )
        enriched_page_result["target_country"] = source.get("target_country")
        enriched_page_results.append(enriched_page_result)

    return enriched_page_results


def count_readable_pages(page_results: list[dict]) -> int:
    return sum(
        1
        for page_result in page_results
        if page_result.get("status") in {"read_success", "cache_hit"}
        and page_result.get("cleaned_text")
    )


def count_failed_pages(page_results: list[dict]) -> int:
    return sum(
        1
        for page_result in page_results
        if page_result.get("status") not in {"read_success", "cache_hit"}
        or not page_result.get("cleaned_text")
    )


def filter_active_scholarships(scholarships: list[dict]) -> list[dict]:
    return [
        scholarship
        for scholarship in scholarships
        if not has_expired_or_closed_scholarship_signal(scholarship)
    ]


def count_scholarships_with_useful_link(scholarships: list[dict]) -> int:
    return sum(
        1
        for scholarship in scholarships
        if normalize_link_fields(scholarship).get("display_link")
    )


def prepare_scholarships_for_matching(scholarships: list[dict]) -> list[dict]:
    prepared_scholarships: list[dict] = []
    for scholarship in scholarships:
        prepared_scholarship = normalize_link_fields(scholarship)
        if not prepared_scholarship["display_link"]:
            continue
        prepared_scholarships.append(prepared_scholarship)

    return dedupe_scholarships_by_best_link(prepared_scholarships)


def filter_ranked_results_with_links(ranked_results: list[dict]) -> list[dict]:
    filtered_results = []
    for result in ranked_results:
        filtered_result = normalize_link_fields(result)
        if not filtered_result["display_link"]:
            continue
        filtered_results.append(filtered_result)
    return filtered_results


def dedupe_scholarships_by_best_link(scholarships: list[dict]) -> list[dict]:
    best_by_key: dict[str, dict] = {}
    for scholarship in scholarships:
        key = get_scholarship_dedupe_key(scholarship)
        current = best_by_key.get(key)
        if current is None or scholarship_quality_key(scholarship) > scholarship_quality_key(
            current
        ):
            best_by_key[key] = scholarship
    return list(best_by_key.values())


def get_scholarship_dedupe_key(scholarship: dict) -> str:
    source_url = first_useful_url(
        scholarship.get("source_url"),
        scholarship.get("url"),
        scholarship.get("link"),
    ).lower()
    name = normalize_optional_text(scholarship.get("scholarship_name")).lower()
    if source_url:
        return f"url:{source_url}"
    return f"name:{name}"


def scholarship_quality_key(scholarship: dict) -> tuple[int, int]:
    return (link_quality_score(scholarship), scholarship_completeness_score(scholarship))


def scholarship_completeness_score(scholarship: dict) -> int:
    meaningful_fields = (
        "scholarship_name",
        "institution",
        "country",
        "deadline",
        "benefits",
        "requirements",
        "eligible_nationalities",
        "required_languages",
        "fields",
        "recommendation_summary",
    )
    return sum(1 for field in meaningful_fields if scholarship.get(field))


def link_quality_score(scholarship: dict) -> int:
    normalized_links = normalize_link_fields(scholarship)
    if normalized_links["official_link"]:
        return 4
    if normalized_links["application_url"]:
        return 3
    if normalized_links["source_url"]:
        return 2
    if normalized_links["pdf_url"]:
        return 1
    return 0


def build_display_link(record: dict) -> str:
    return normalize_link_fields(record)["display_link"]


def normalize_link_fields(record: dict) -> dict:
    normalized_record = dict(record)
    source_url = first_useful_url(
        record.get("source_url"),
        record.get("url"),
        record.get("link"),
        record.get("original_url"),
    )
    official_link = first_useful_url(
        record.get("official_link"),
        record.get("official_url"),
    )
    application_url = first_useful_url(
        record.get("application_url"),
        record.get("apply_url"),
    )
    pdf_url = normalize_useful_url(record.get("pdf_url"))
    display_link = first_useful_url(
        official_link,
        application_url,
        source_url,
        pdf_url,
        record.get("display_link"),
    )
    normalized_record.update(
        {
            "source_url": source_url,
            "official_link": official_link,
            "application_url": application_url,
            "pdf_url": pdf_url,
            "display_link": display_link,
        }
    )
    return normalized_record


def has_expired_or_closed_scholarship_signal(scholarship: dict) -> bool:
    status = detect_status_from_deadline(
        scholarship.get("deadline"),
        scholarship.get("application_status"),
    )
    if status in {"closed", "expired"}:
        return True

    evidence_text = " ".join(normalize_string_list(scholarship.get("evidence_snippets")))
    return has_obvious_expired_signal(
        normalize_optional_text(scholarship.get("scholarship_name")),
        " ".join(
            [
                normalize_optional_text(scholarship.get("deadline")),
                normalize_optional_text(scholarship.get("application_status")),
                evidence_text,
            ]
        ),
    )


def normalize_pipeline_errors(prefix: str, errors: Any) -> list[str]:
    if not isinstance(errors, list):
        return []

    normalized_errors: list[str] = []
    for error in errors:
        if isinstance(error, dict):
            target = (
                normalize_optional_text(error.get("scholarship_name"))
                or normalize_optional_text(error.get("title"))
                or normalize_optional_text(error.get("url"))
                or "record"
            )
            message = normalize_optional_text(error.get("error"))
            if message:
                normalized_errors.append(f"{prefix} error for {target}: {message}")
        else:
            message = normalize_optional_text(error)
            if message:
                normalized_errors.append(f"{prefix} error: {message}")

    return normalized_errors


def build_empty_metrics() -> dict[str, int]:
    return {
        "generated_queries_count": 0,
        "sources_found_count": 0,
        "sources_deduplicated_count": 0,
        "sources_accepted_count": 0,
        "sources_accepted_with_warning_count": 0,
        "sources_rejected_count": 0,
        "pages_read_count": 0,
        "pages_failed_count": 0,
        "scholarships_extracted_count": 0,
        "scholarships_with_useful_link_count": 0,
        "expired_rejected_count": 0,
        "matched_count": 0,
        "ranked_count": 0,
        "recommended_count": 0,
        "less_recommended_count": 0,
    }


def build_empty_rejection_summary() -> dict[str, int]:
    return {
        "non_scholarship_page": 0,
        "untrusted_source": 0,
        "expired_or_closed": 0,
        "no_useful_link": 0,
        "duplicate": 0,
        "read_failed": 0,
        "extraction_failed": 0,
    }


def normalize_metrics(value: Any) -> dict[str, int]:
    metrics = build_empty_metrics()
    if isinstance(value, dict):
        for key in metrics:
            metrics[key] = normalize_count(value.get(key))
    return metrics


def normalize_rejection_summary(value: Any) -> dict[str, int]:
    summary = build_empty_rejection_summary()
    if isinstance(value, dict):
        for key in summary:
            summary[key] = normalize_count(value.get(key))
    return summary


def normalize_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, count)


def summarize_source_rejections(validated_sources: list[dict]) -> dict[str, int]:
    summary = build_empty_rejection_summary()
    for source in validated_sources:
        validation_status = normalize_optional_text(
            source.get("validation_status") or source.get("acceptance_status")
        ).lower()
        decision = normalize_optional_text(source.get("decision")).lower()
        if validation_status != "rejected" and decision != "reject":
            continue

        source_type = normalize_optional_text(source.get("source_type")).lower()
        risk_flags = {
            normalize_optional_text(flag).lower()
            for flag in source.get("risk_flags", [])
            if normalize_optional_text(flag)
        }
        if source_type in {"irrelevant"} or "low_relevance" in risk_flags:
            summary["non_scholarship_page"] += 1
        elif source_type == "expired_or_closed" or "expired_or_closed" in risk_flags:
            summary["expired_or_closed"] += 1
        else:
            summary["untrusted_source"] += 1
    return summary


def merge_rejection_summary(target: dict[str, int], addition: dict[str, int]) -> None:
    for key, value in addition.items():
        target[key] = int(target.get(key, 0)) + int(value or 0)


def ensure_required_workflow_steps(workflow_steps: list[dict]) -> list[dict]:
    existing_names = {
        normalize_optional_text(step.get("step_name"))
        for step in workflow_steps
        if isinstance(step, dict)
    }
    completed_steps = list(workflow_steps)
    for step_name in REQUIRED_SEARCH_STEP_NAMES:
        if step_name in existing_names:
            continue
        completed_steps.append(
            build_workflow_step(
                step_name,
                "skipped",
                0,
                "Step was not reached because live search stopped earlier.",
            )
        )
    return completed_steps


def build_search_signature(normalized_profile: dict):
    signature_payload = {
        "scholarship_type": normalize_signature_value(
            normalized_profile.get("scholarship_type")
        ),
        "languages": normalize_signature_languages(normalized_profile.get("languages")),
        "nationality": normalize_signature_value(normalized_profile.get("nationality")),
        "budget": normalize_signature_budget(normalized_profile.get("budget")),
    }
    modality = normalize_signature_value(normalized_profile.get("preferred_modality"))
    if modality in {"online", "on-campus", "hybrid"}:
        signature_payload["modality"] = modality

    signature_json = json.dumps(
        signature_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "key": hashlib.sha256(signature_json.encode("utf-8")).hexdigest(),
        "payload": signature_payload,
        "filter_order": build_filtering_layers(normalized_profile),
    }


def build_filtering_layers(normalized_profile: dict):
    layers = [
        {
            "layer": 1,
            "field": "scholarship_type",
            "value": normalized_profile.get("scholarship_type"),
        },
        {
            "layer": 2,
            "field": "languages",
            "value": normalized_profile.get("languages", []),
        },
        {
            "layer": 3,
            "field": "nationality",
            "value": normalized_profile.get("nationality"),
        },
        {
            "layer": 4,
            "field": "budget",
            "value": normalized_profile.get("budget"),
        },
    ]
    modality = normalize_signature_value(normalized_profile.get("preferred_modality"))
    if modality in {"online", "on-campus", "hybrid"}:
        layers.append(
            {
                "layer": 5,
                "field": "modality",
                "value": normalized_profile.get("preferred_modality"),
            }
        )
    return layers


def normalize_signature_value(value: Any):
    return normalize_optional_text(value).lower()


def normalize_signature_languages(value: Any):
    if not isinstance(value, list):
        return []

    languages = []
    for language_entry in value:
        if isinstance(language_entry, dict):
            language = normalize_signature_value(language_entry.get("language"))
            level = normalize_signature_value(language_entry.get("level"))
            if language:
                languages.append({"language": language, "level": level})
        else:
            language = normalize_signature_value(language_entry)
            if language:
                languages.append({"language": language, "level": ""})
    return sorted(languages, key=lambda item: (item["language"], item["level"]))


def normalize_signature_budget(value: Any):
    if not isinstance(value, dict):
        return {
            "currency": "usd",
            "max_personal_contribution": None,
        }

    contribution = value.get("max_personal_contribution")
    if contribution == "":
        contribution = None
    return {
        "currency": normalize_signature_value(value.get("currency") or "usd"),
        "max_personal_contribution": contribution,
    }


def load_latest_demo_payload():
    demo_dir = settings.DEMO_OUTPUT_DIR
    if not demo_dir.exists():
        return None

    demo_files = sorted(
        demo_dir.glob("demo_result_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not demo_files:
        return None

    latest_demo_path = demo_files[0]
    try:
        return json.loads(latest_demo_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def normalize_frontend_response(
    payload: dict,
    status_override: str,
    message: str,
    extra_workflow_steps: list[dict] | None = None,
    errors: list[str] | None = None,
):
    ranked_results = normalize_recommendation_list(find_recommendation_records(payload))
    recommended, less_recommended = split_recommendations(ranked_results)
    workflow_steps = extra_workflow_steps or normalize_workflow_steps(
        payload.get("workflow_steps", [])
    )
    response_errors = [
        *normalize_error_list(payload.get("errors", [])),
        *(errors or []),
    ]

    if not ranked_results:
        return build_empty_response(
            message=message
            or "No scholarship recommendations were found for this profile.",
            workflow_steps=workflow_steps,
            errors=response_errors,
            status=status_override if status_override in {"failed", "empty"} else "empty",
        )

    status = status_override or "ok"
    if status == "failed" and ranked_results:
        status = "partial_failure"

    return {
        "status": status,
        "message": message,
        "workflow_steps": workflow_steps,
        "metrics": normalize_metrics(payload.get("metrics")),
        "rejection_summary": normalize_rejection_summary(
            payload.get("rejection_summary")
        ),
        "ranked_results": ranked_results,
        "recommended": recommended,
        "less_recommended": less_recommended,
        "top_recommendations": ranked_results,
        "recommendations": ranked_results,
        "results": ranked_results,
        "errors": dedupe_text_values(response_errors),
    }


def build_empty_response(
    message: str,
    workflow_steps: list[dict] | None = None,
    errors: list[str] | None = None,
    status: str = "empty",
):
    return {
        "status": status,
        "message": message,
        "workflow_steps": workflow_steps or [],
        "metrics": build_empty_metrics(),
        "rejection_summary": build_empty_rejection_summary(),
        "ranked_results": [],
        "recommended": [],
        "less_recommended": [],
        "errors": errors or [],
    }


def find_recommendation_records(payload: dict):
    for key in (
        "ranked_results",
        "top_recommendations",
        "recommendations",
        "results",
        "scholarships",
        "matches",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def normalize_recommendation_list(records: list[Any]):
    normalized_results = []
    seen_keys: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue

        normalized_result = normalize_recommendation(record, index)
        if not normalize_optional_text(normalized_result.get("display_link")):
            continue
        dedupe_key = get_recommendation_key(normalized_result)
        if dedupe_key in seen_keys:
            continue

        seen_keys.add(dedupe_key)
        normalized_results.append(normalized_result)

    return normalized_results


def normalize_recommendation(record: dict, index: int):
    normalized_links = normalize_link_fields(record)
    final_score = normalize_score(record.get("final_score"))
    compatibility_score = normalize_score(record.get("compatibility_score"))
    eligibility_decision = normalize_optional_text(
        record.get("eligibility_decision")
    ) or "insufficient_information"
    priority_label = normalize_priority_label(
        record.get("priority_label") or eligibility_decision or final_score
    )

    return {
        "id": normalize_optional_text(record.get("id")) or f"backend-result-{index + 1}",
        "rank": record.get("rank") or index + 1,
        "scholarship_name": normalize_optional_text(
            record.get("scholarship_name") or record.get("name")
        )
        or "Untitled scholarship",
        "source_url": normalized_links["source_url"],
        "official_link": normalized_links["official_link"],
        "application_url": normalized_links["application_url"],
        "pdf_url": normalized_links["pdf_url"],
        "display_link": normalized_links["display_link"],
        "final_score": final_score,
        "compatibility_score": compatibility_score,
        "eligibility_decision": eligibility_decision,
        "priority_label": priority_label,
        "recommendation_summary": normalize_optional_text(
            record.get("recommendation_summary")
            or record.get("recommendation_reason")
            or record.get("summary")
        )
        or "No recommendation summary was provided.",
        "ranking_reasons": normalize_string_list(record.get("ranking_reasons")),
        "risk_factors": normalize_string_list(record.get("risk_factors")),
        "missing_requirements": normalize_string_list(
            record.get("missing_requirements")
        ),
    }


def split_recommendations(ranked_results: list[dict]):
    recommended = []
    less_recommended = []
    low_priority_candidates = []

    sorted_results = sort_recommendation_records(ranked_results)

    for result in sorted_results:
        priority_label = normalize_optional_text(result.get("priority_label")).lower()
        final_score = normalize_score(result.get("final_score"))
        if priority_label in RECOMMENDED_LABELS:
            recommended.append(result)
        elif priority_label == "low_priority":
            low_priority_candidates.append(result)
            less_recommended.append(result)
        elif priority_label in LESS_RECOMMENDED_LABELS or final_score < 65:
            less_recommended.append(result)
        elif final_score >= 60:
            recommended.append(result)
        else:
            less_recommended.append(result)

    if not recommended and low_priority_candidates:
        recommended = [
            result
            for result in low_priority_candidates
            if normalize_score(result.get("final_score")) >= 45
        ] or low_priority_candidates
        less_recommended = [
            result for result in less_recommended if result not in recommended
        ]

    return recommended, less_recommended[:LESS_RECOMMENDED_DISPLAY_LIMIT]


def sort_recommendation_records(results: list[dict]) -> list[dict]:
    return sorted(
        results,
        key=lambda result: (
            -normalize_score(result.get("final_score")),
            -normalize_score(result.get("compatibility_score")),
            normalize_rank(result.get("rank")),
        ),
    )


def normalize_rank(value: Any) -> int:
    try:
        rank = int(value)
    except (TypeError, ValueError):
        return 1_000_000
    return rank if rank > 0 else 1_000_000


def normalize_workflow_steps(steps: Any):
    if not isinstance(steps, list):
        return []

    return [
        build_workflow_step(
            normalize_optional_text(
                step.get("step_name") or step.get("label") or step.get("name")
            )
            or f"Workflow step {index + 1}",
            normalize_workflow_status(step.get("status")),
            int(step.get("count") or 0),
            normalize_optional_text(step.get("message")),
        )
        for index, step in enumerate(steps)
        if isinstance(step, dict)
    ]


def build_workflow_step(step_name: str, status: str, count: int, message: str):
    return {
        "step_name": step_name,
        "status": normalize_workflow_status(status),
        "count": count,
        "message": message,
    }


def normalize_workflow_status(value: Any):
    status = normalize_optional_text(value).lower()
    if status in {"pending", "active", "completed", "failed", "skipped"}:
        return status
    if status in {"success", "ok", "done"}:
        return "completed"
    if status in {"partial", "partial_failure"}:
        return "completed"
    return "pending"


def normalize_status(value: Any, default: str):
    status = normalize_optional_text(value).lower()
    if status in {"ok", "partial_failure", "fallback_demo", "empty"}:
        return status
    if status == "success":
        return "ok"
    if status == "failed":
        return "partial_failure"
    return default


def normalize_priority_label(value: Any):
    if isinstance(value, (int, float)):
        return "medium_priority" if value >= 65 else "low_priority"

    priority = normalize_optional_text(value).lower()
    if priority in {
        "high_priority",
        "medium_priority",
        "possible_match",
        "low_priority",
        "insufficient_information",
        "not_recommended",
        "rejected",
    }:
        return priority
    if priority in {"confirmed_match", "likely_match", "strong_match"}:
        return "high_priority"
    if priority == "weak_match":
        return "low_priority"
    if priority == "insufficient_information":
        return "insufficient_information"
    if priority in {"not_eligible", "mismatch"}:
        return "not_recommended"
    if priority == "rejected":
        return "rejected"
    return "not_recommended"


def count_recommendations(payload: dict):
    return len(find_recommendation_records(payload))


def get_recommendation_key(result: dict):
    source_url = first_useful_url(
        result.get("display_link"),
        result.get("official_link"),
        result.get("application_url"),
        result.get("source_url"),
        result.get("pdf_url"),
    ).lower()
    if source_url:
        return f"url:{source_url}"
    return f"name:{normalize_optional_text(result.get('scholarship_name')).lower()}"


def normalize_score(value: Any):
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, int(round(score))))


def normalize_string_list(value: Any):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_error_list(value: Any):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def dedupe_text_values(values: list[str]):
    seen = set()
    cleaned_values = []
    for value in values:
        cleaned_value = str(value).strip()
        if not cleaned_value:
            continue
        key = cleaned_value.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned_values.append(cleaned_value)
    return cleaned_values


def normalize_optional_text(value: Any):
    if value is None:
        return ""
    return str(value).strip()


def parse_multipart_body(body: bytes, content_type: str):
    boundary = get_multipart_boundary(content_type)
    delimiter = b"--" + boundary.encode("utf-8")
    fields: Dict[str, str] = {}
    files: Dict[str, str] = {}

    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue

        if part.endswith(b"--"):
            part = part[:-2].rstrip(b"\r\n")

        header_bytes, separator, content = part.partition(b"\r\n\r\n")
        if not separator:
            continue

        headers = header_bytes.decode("utf-8", errors="replace").split("\r\n")
        disposition = get_header_value(headers, "content-disposition")
        if not disposition:
            continue

        disposition_params = parse_header_parameters(disposition)
        field_name = disposition_params.get("name", "")
        filename = disposition_params.get("filename", "")
        if not field_name:
            continue

        content = content.rstrip(b"\r\n")
        if filename:
            files[field_name] = filename
        else:
            fields[field_name] = content.decode("utf-8", errors="replace")

    return fields, files


def get_multipart_boundary(content_type: str):
    for part in content_type.split(";"):
        key, separator, value = part.strip().partition("=")
        if separator and key.lower() == "boundary":
            boundary = value.strip().strip('"')
            if boundary:
                return boundary

    raise ValueError("Missing multipart boundary.")


def get_header_value(headers: list[str], header_name: str):
    header_prefix = f"{header_name.lower()}:"
    for header in headers:
        if header.lower().startswith(header_prefix):
            return header.split(":", 1)[1].strip()
    return ""


def parse_header_parameters(header_value: str):
    parameters: Dict[str, str] = {}
    for item in header_value.split(";"):
        key, separator, value = item.strip().partition("=")
        if separator:
            parameters[key.lower()] = value.strip().strip('"')
    return parameters
