from __future__ import annotations

import json
import re
import hashlib
import unicodedata
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
    "strong_match",
    "possible_match",
}
LESS_RECOMMENDED_LABELS = {
    "low_priority",
    "not_recommended",
    "weak_match",
    "not_eligible",
    "insufficient_information",
}
REQUIRED_SEARCH_STEP_NAMES = (
    "Reading profile input",
    "Normalizing profile",
    "Generating global scholarship search queries",
    "Searching global scholarship sources",
    "Validating official scholarship sources",
    "Reading scholarship pages",
    "Extracting scholarship data",
    "Matching scholarships with profile",
    "Ranking recommendations",
    "Preparing final results",
)
SOURCE_POLICY_ALLOWED_TYPES = {
    "official_university",
    "official_government",
    "official_organization",
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
        completed_profile = infer_profile_from_text(raw_profile_text, "")

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
    matching_results: list[dict] = []
    ranked_results: list[dict] = []

    try:
        queries = QUERY_AGENT.generate_queries(normalized_profile)
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
        workflow_steps.append(
            build_workflow_step(
                "Searching global scholarship sources",
                "completed",
                len(candidate_results),
                f"Collected {len(candidate_results)} candidate scholarship sources.",
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
        rejected_by_policy = len(validated_sources) - len(accepted_sources)
        workflow_steps.append(
            build_workflow_step(
                "Validating official scholarship sources",
                "completed",
                len(accepted_sources),
                (
                    f"Accepted {len(accepted_sources)} official or trusted sources "
                    f"from {len(validated_sources)} validated candidates."
                    + (
                        f" Rejected {rejected_by_policy} sources by policy."
                        if rejected_by_policy
                        else ""
                    )
                ),
            )
        )
    except Exception as exc:
        return build_failed_pipeline_payload(
            workflow_steps,
            "Validating official scholarship sources",
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
        workflow_steps.append(
            build_workflow_step(
                "Reading scholarship pages",
                "completed",
                readable_page_count,
                (
                    f"Read {readable_page_count} scholarship pages from "
                    f"{len(accepted_sources)} accepted sources."
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
        expired_count = len(scholarships) - len(active_scholarships)
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
                len(active_scholarships),
                (
                    f"Extracted {len(active_scholarships)} active scholarship records."
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
        matching_payload = run_matching(normalized_profile, active_scholarships)
        matching_results = matching_payload["matching_results"]
        matching_summary = matching_payload["summary"]
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
        ranked_results = ranking_payload["ranked_results"]
        ranking_summary = ranking_payload["summary"]
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
    }


def filter_policy_accepted_sources(validated_sources: list[dict]) -> list[dict]:
    return [
        source for source in validated_sources if is_policy_accepted_source(source)
    ]


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
    sources_by_url = {source.get("url"): source for source in validated_sources}
    enriched_page_results: list[dict] = []

    for page_result in page_results:
        source = sources_by_url.get(page_result.get("url"), {})
        enriched_page_result = dict(page_result)
        enriched_page_result["source_reliability_score"] = source.get(
            "reliability_score"
        )
        enriched_page_results.append(enriched_page_result)

    return enriched_page_results


def count_readable_pages(page_results: list[dict]) -> int:
    return sum(
        1
        for page_result in page_results
        if page_result.get("status") in {"read_success", "cache_hit"}
        and page_result.get("cleaned_text")
    )


def filter_active_scholarships(scholarships: list[dict]) -> list[dict]:
    return [
        scholarship
        for scholarship in scholarships
        if not has_expired_or_closed_scholarship_signal(scholarship)
    ]


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


def infer_profile_from_text(raw_profile_text: str, scholarship_goal: str):
    combined_text = " ".join(
        text for text in [raw_profile_text, scholarship_goal] if text
    )
    normalized_text = normalize_for_detection(combined_text)

    target_countries = detect_values(
        normalized_text,
        {
            "canada": "Canada",
            "germany": "Germany",
            "alemania": "Germany",
            "netherlands": "Netherlands",
            "holanda": "Netherlands",
            "united states": "United States",
            "usa": "United States",
            "estados unidos": "United States",
            "spain": "Spain",
            "espana": "Spain",
            "france": "France",
            "francia": "France",
            "uk": "United Kingdom",
            "united kingdom": "United Kingdom",
            "reino unido": "United Kingdom",
        },
    )
    interests = detect_values(
        normalized_text,
        {
            "artificial intelligence": "Artificial Intelligence",
            "inteligencia artificial": "Artificial Intelligence",
            "data science": "Data Science",
            "ciencia de datos": "Data Science",
            "computer science": "Computer Science",
            "systems engineering": "Systems Engineering",
            "ingenieria de sistemas": "Systems Engineering",
            "diseno grafico": "Graphic Design",
            "diseno grafico": "Graphic Design",
            "graphic design": "Graphic Design",
            "arte": "Art",
            "art": "Art",
            "cybersecurity": "Cybersecurity",
            "ciberseguridad": "Cybersecurity",
            "machine learning": "Machine Learning",
        },
    )

    nationality = first_detected_value(
        normalized_text,
        {
            "colombian": "Colombian",
            "colombiano": "Colombian",
            "colombiana": "Colombian",
            "mexican": "Mexican",
            "mexicano": "Mexican",
            "peruvian": "Peruvian",
            "peruano": "Peruvian",
            "argentinian": "Argentinian",
            "argentino": "Argentinian",
        },
        "International",
    )
    academic_level = first_detected_value(
        normalized_text,
        {
            "phd": "phd",
            "doctorado": "phd",
            "doctoral": "phd",
            "master": "masters",
            "maestria": "masters",
            "maestria": "masters",
            "bachelor": "bachelors",
            "pregrado": "bachelors",
            "undergraduate": "bachelors",
        },
        "bachelors",
    )
    scholarship_type = "Full or partial funding"
    if "full funding" in normalized_text or "beca completa" in normalized_text:
        scholarship_type = "Full funding"
    elif "partial" in normalized_text or "parcial" in normalized_text:
        scholarship_type = "Partial funding"

    field_of_study = interests[0] if interests else "General studies"
    languages = infer_languages(normalized_text)

    return {
        "nationality": nationality,
        "country_of_residence": infer_country_of_residence(normalized_text, nationality),
        "languages": languages or [{"language": "English", "level": "B2"}],
        "academic_level": academic_level,
        "field_of_study": field_of_study,
        "interests": interests or [field_of_study],
        "target_countries": target_countries or ["Canada", "Germany", "Netherlands"],
        "scholarship_type": scholarship_type,
        "budget": {
            "currency": "usd",
            "max_personal_contribution": None,
        },
        "preferred_modality": infer_modality(normalized_text),
    }


def complete_profile_defaults(profile: dict):
    completed_profile = dict(profile)
    completed_profile.setdefault("nationality", "International")
    completed_profile.setdefault("country_of_residence", completed_profile["nationality"])
    completed_profile.setdefault(
        "languages",
        [{"language": "English", "level": "B2"}],
    )
    completed_profile.setdefault("academic_level", "bachelors")
    completed_profile.setdefault("field_of_study", "General studies")
    completed_profile.setdefault("interests", [completed_profile["field_of_study"]])
    completed_profile.setdefault(
        "target_countries",
        ["Canada", "Germany", "Netherlands"],
    )
    completed_profile.setdefault("scholarship_type", "Full or partial funding")
    completed_profile.setdefault(
        "budget",
        {"currency": "usd", "max_personal_contribution": None},
    )
    completed_profile.setdefault("preferred_modality", "Any")
    return completed_profile


def normalize_for_detection(value: str):
    normalized_value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character
        for character in normalized_value
        if not unicodedata.combining(character)
    )


def infer_languages(normalized_text: str):
    languages = []
    if "spanish" in normalized_text or "espanol" in normalized_text:
        languages.append(
            {
                "language": "Spanish",
                "level": detect_language_level(normalized_text, "spanish")
                or detect_language_level(normalized_text, "espanol")
                or "Native",
            }
        )
    if "english" in normalized_text or "ingles" in normalized_text:
        languages.append(
            {
                "language": "English",
                "level": detect_language_level(normalized_text, "english")
                or detect_language_level(normalized_text, "ingles")
                or "B2",
            }
        )
    if "french" in normalized_text or "frances" in normalized_text:
        languages.append(
            {
                "language": "French",
                "level": detect_language_level(normalized_text, "french")
                or detect_language_level(normalized_text, "frances")
                or "B1",
            }
        )
    return languages


def detect_language_level(normalized_text: str, language_key: str):
    pattern = rf"{re.escape(language_key)}\s+(native|a1|a2|b1|b2|c1|c2)"
    match = re.search(pattern, normalized_text)
    if not match:
        return ""

    level = match.group(1)
    return "Native" if level == "native" else level.upper()


def infer_country_of_residence(normalized_text: str, nationality: str):
    if "colombia" in normalized_text:
        return "Colombia"
    if nationality == "Colombian":
        return "Colombia"
    return nationality


def infer_modality(normalized_text: str):
    if "online" in normalized_text or "virtual" in normalized_text:
        return "Online"
    if "hybrid" in normalized_text or "hibrido" in normalized_text:
        return "Hybrid"
    if "campus" in normalized_text or "presencial" in normalized_text:
        return "On-campus"
    return "Any"


def detect_values(normalized_text: str, values_by_keyword: dict[str, str]):
    values = []
    for keyword, value in values_by_keyword.items():
        if keyword in normalized_text and value not in values:
            values.append(value)
    return values


def first_detected_value(
    normalized_text: str,
    values_by_keyword: dict[str, str],
    default: str,
):
    for keyword, value in values_by_keyword.items():
        if keyword in normalized_text:
            return value
    return default


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
        dedupe_key = get_recommendation_key(normalized_result)
        if dedupe_key in seen_keys:
            continue

        seen_keys.add(dedupe_key)
        normalized_results.append(normalized_result)

    return normalized_results


def normalize_recommendation(record: dict, index: int):
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
        "source_url": normalize_optional_text(
            record.get("source_url")
            or record.get("official_link")
            or record.get("url")
            or record.get("link")
        ),
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

    for result in ranked_results:
        priority_label = normalize_optional_text(result.get("priority_label")).lower()
        final_score = normalize_score(result.get("final_score"))
        if priority_label in RECOMMENDED_LABELS or final_score >= 65:
            recommended.append(result)
        elif priority_label == "low_priority":
            low_priority_candidates.append(result)
            less_recommended.append(result)
        elif priority_label in LESS_RECOMMENDED_LABELS or final_score < 65:
            less_recommended.append(result)
        else:
            less_recommended.append(result)

    if not recommended and low_priority_candidates:
        recommended = low_priority_candidates[:]
        less_recommended = [
            result for result in less_recommended if result not in recommended
        ]

    return recommended, less_recommended


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
    if priority in {"high_priority", "medium_priority", "low_priority", "not_recommended"}:
        return priority
    if priority == "strong_match":
        return "high_priority"
    if priority == "possible_match":
        return "medium_priority"
    if priority == "weak_match":
        return "low_priority"
    if priority in {"not_eligible", "insufficient_information"}:
        return "not_recommended"
    return "not_recommended"


def count_recommendations(payload: dict):
    return len(find_recommendation_records(payload))


def get_recommendation_key(result: dict):
    source_url = normalize_optional_text(result.get("source_url")).lower()
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
