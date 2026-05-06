from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent.extraction_agent import ExtractionAgent
from agent.page_reader_agent import PageReaderAgent
from agent.profile_agent import ProfileAgent
from agent.query_agent import QueryAgent, QueryGenerationError
from agent.search_agent import SearchAgent
from agent.source_validator_agent import SourceValidatorAgent
from config.settings import settings
from llm.provider import LLMProviderError, generate_text
from schemas.match_schema import MatchValidationError
from schemas.profile_schema import ProfileValidationError, validate_profile
from schemas.refresh_schema import RefreshValidationError
from schemas.ranking_schema import RankingValidationError
from schemas.retrieval_schema import RetrievalValidationError
from services.refresh_service import RefreshService
from services.matching_service import run_matching
from services.ranking_service import run_ranking
from services.retrieval_service import run_retrieval
from services.scholarship_service import save_to_knowledge_base
from utils.json_handler import JsonHandlerError, load_json, save_json
from utils.logger import get_logger


logger = get_logger(__name__)
TEST_PROMPT_PATH = settings.PROJECT_ROOT / "prompts" / "test_qwen_connection.txt"
profile_agent = ProfileAgent()
query_agent = QueryAgent()
search_agent = SearchAgent()
source_validator_agent = SourceValidatorAgent()
page_reader_agent = PageReaderAgent()
extraction_agent = ExtractionAgent()


def build_output_payload(profile: dict, profile_path: Path, output_path: Path) -> dict:
    return {
        "status": "profile_prepared",
        "phase": "phase_3_profile_intelligence",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": profile,
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": False,
            "web_search_performed": False,
            "rag_used": False,
            "database_used": False,
        },
    }


def build_query_output_payload(
    normalized_profile: dict,
    queries: list[dict],
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "queries_generated",
        "phase": "phase_4_query_generation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "queries": queries,
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": True,
            "queries_generated": True,
            "web_search_performed": False,
            "source_validation_performed": False,
            "scholarship_extraction_performed": False,
            "rag_used": False,
            "database_used": False,
        },
    }


def build_search_output_payload(
    normalized_profile: dict,
    queries: list[dict],
    candidate_results: list[dict],
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "search_results_collected",
        "phase": "phase_5_web_search",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "queries": queries,
        "candidate_results": candidate_results,
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": True,
            "queries_generated": True,
            "web_search_performed": True,
            "page_reading_performed": False,
            "source_validation_performed": False,
            "scholarship_extraction_performed": False,
            "rag_used": False,
            "database_used": False,
        },
    }


def build_source_validation_output_payload(
    normalized_profile: dict,
    queries: list[dict],
    candidate_results: list[dict],
    validated_sources: list[dict],
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "sources_validated",
        "phase": "phase_6_source_intelligence",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "queries": queries,
        "candidate_results": candidate_results,
        "validated_sources": validated_sources,
        "source_counts": count_source_decisions(validated_sources),
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": True,
            "queries_generated": True,
            "web_search_performed": True,
            "source_validation_performed": True,
            "page_reading_performed": False,
            "scholarship_extraction_performed": False,
            "rag_used": False,
            "database_used": False,
        },
    }


def build_page_output_payload(
    normalized_profile: dict,
    queries: list[dict],
    candidate_results: list[dict],
    validated_sources: list[dict],
    page_results: list[dict],
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "pages_read_and_cleaned",
        "phase": "phase_7_page_reading_cleaning",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "queries": queries,
        "candidate_results": candidate_results,
        "validated_sources": validated_sources,
        "page_results": page_results,
        "source_counts": count_source_decisions(validated_sources),
        "page_counts": count_page_statuses(page_results),
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": True,
            "queries_generated": True,
            "web_search_performed": True,
            "source_validation_performed": True,
            "page_reading_performed": True,
            "scholarship_extraction_performed": False,
            "rag_used": False,
            "database_used": False,
        },
    }


def build_extraction_output_payload(
    normalized_profile: dict,
    queries: list[dict],
    candidate_results: list[dict],
    validated_sources: list[dict],
    page_results: list[dict],
    scholarships: list[dict],
    extraction_errors: list[dict],
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "scholarships_extracted",
        "phase": "phase_8_scholarship_extraction",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "queries": queries,
        "candidate_results": candidate_results,
        "validated_sources": validated_sources,
        "page_results": page_results,
        "scholarships": scholarships,
        "extraction_errors": extraction_errors,
        "source_counts": count_source_decisions(validated_sources),
        "page_counts": count_page_statuses(page_results),
        "extraction_counts": {
            "scholarships": len(scholarships),
            "errors": len(extraction_errors),
        },
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": True,
            "queries_generated": True,
            "web_search_performed": True,
            "source_validation_performed": True,
            "page_reading_performed": True,
            "scholarship_extraction_performed": True,
            "rag_used": False,
            "database_used": False,
            "matching_performed": False,
            "ranking_performed": False,
        },
    }


def build_knowledge_base_output_payload(
    normalized_profile: dict,
    queries: list[dict],
    validated_sources: list[dict],
    scholarships: list[dict],
    extraction_errors: list[dict],
    save_summary: dict,
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "knowledge_base_saved",
        "phase": "phase_9_knowledge_base",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "queries": queries,
        "validated_sources": validated_sources,
        "scholarships": scholarships,
        "extraction_errors": extraction_errors,
        "save_summary": save_summary,
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": True,
            "queries_generated": True,
            "web_search_performed": True,
            "source_validation_performed": True,
            "page_reading_performed": True,
            "scholarship_extraction_performed": True,
            "knowledge_base_saved": True,
            "rag_used": False,
            "database_used": True,
            "matching_performed": False,
            "ranking_performed": False,
        },
    }


def build_matching_output_payload(
    normalized_profile: dict,
    queries: list[dict],
    validated_sources: list[dict],
    scholarships: list[dict],
    matching_results: list[dict],
    matching_summary: dict,
    extraction_errors: list[dict],
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "scholarships_matched",
        "phase": "phase_11_eligibility_matching",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "queries": queries,
        "validated_sources": validated_sources,
        "scholarships": scholarships,
        "matching_results": matching_results,
        "matching_summary": matching_summary,
        "extraction_errors": extraction_errors,
        "matching_score_version": settings.MATCHING_SCORE_VERSION,
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": True,
            "queries_generated": True,
            "web_search_performed": True,
            "source_validation_performed": True,
            "page_reading_performed": True,
            "scholarship_extraction_performed": True,
            "knowledge_base_saved": False,
            "matching_performed": True,
            "ranking_performed": False,
            "rag_used": False,
            "database_used": False,
        },
    }


def build_ranking_output_payload(
    normalized_profile: dict,
    queries: list[dict],
    validated_sources: list[dict],
    scholarships: list[dict],
    matching_results: list[dict],
    matching_summary: dict,
    ranked_results: list[dict],
    ranking_summary: dict,
    extraction_errors: list[dict],
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "scholarships_ranked",
        "phase": "phase_12_ranking_recommendation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "queries": queries,
        "validated_sources": validated_sources,
        "scholarships": scholarships,
        "matching_results": matching_results,
        "matching_summary": matching_summary,
        "ranked_recommendations": ranked_results,
        "ranking_summary": ranking_summary,
        "extraction_errors": extraction_errors,
        "matching_score_version": settings.MATCHING_SCORE_VERSION,
        "ranking_score_version": settings.RANKING_SCORE_VERSION,
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "llm_called": True,
            "queries_generated": True,
            "web_search_performed": True,
            "source_validation_performed": True,
            "page_reading_performed": True,
            "scholarship_extraction_performed": True,
            "knowledge_base_saved": False,
            "matching_performed": True,
            "ranking_performed": True,
            "rag_used": False,
            "database_used": False,
            "refresh_performed": False,
        },
    }


def build_retrieval_output_payload(
    normalized_profile: dict,
    retrieval_results: list[dict],
    retrieval_summary: dict,
    profile_path: Path,
    output_path: Path,
) -> dict:
    return {
        "status": "known_scholarships_retrieved",
        "phase": "phase_10_rag_retrieval",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_profile": str(profile_path),
        "output_file": str(output_path),
        "normalized_profile": normalized_profile,
        "retrieval_results": retrieval_results,
        "retrieval_summary": retrieval_summary,
        "retrieval_mode": settings.RETRIEVAL_MODE,
        "pipeline": {
            "profile_loaded": True,
            "profile_validated": True,
            "profile_normalized": True,
            "retrieval_performed": True,
            "llm_called": False,
            "web_search_performed": False,
            "page_reading_performed": False,
            "scholarship_extraction_performed": False,
            "matching_performed": False,
            "ranking_performed": False,
            "rag_used": True,
            "database_used": True,
        },
    }


def build_refresh_output_payload(
    refresh_results: list[dict],
    refresh_summary: dict,
    output_path: Path,
) -> dict:
    return {
        "status": "known_scholarships_refreshed",
        "phase": "phase_13_refresh_scalability",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_file": str(output_path),
        "refresh_results": refresh_results,
        "refresh_summary": refresh_summary,
        "pipeline": {
            "refresh_performed": True,
            "llm_called": False,
            "web_search_performed": False,
            "page_reading_performed": settings.REFRESH_CHECK_PAGES,
            "scholarship_extraction_performed": False,
            "matching_performed": False,
            "ranking_performed": False,
            "rag_used": False,
            "database_used": True,
        },
    }


def count_source_decisions(validated_sources: list[dict]) -> dict:
    counts = {"accept": 0, "review": 0, "reject": 0}
    for source in validated_sources:
        decision = source.get("decision")
        if decision in counts:
            counts[decision] += 1
    return counts


def enrich_page_results_with_source_metadata(
    page_results: list[dict], validated_sources: list[dict]
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


def count_page_statuses(page_results: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for page_result in page_results:
        status = str(page_result.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Scholarship Search Agent base CLI with a profile JSON."
    )
    parser.add_argument(
        "--profile",
        default=str(settings.DEFAULT_PROFILE_PATH),
        help="Path to the profile JSON file.",
    )
    parser.add_argument(
        "--test-llm",
        action="store_true",
        help="Call the configured local LLM with a short test prompt.",
    )
    parser.add_argument(
        "--generate-queries",
        action="store_true",
        help="Generate scholarship search queries from the normalized profile.",
    )
    parser.add_argument(
        "--search-web",
        action="store_true",
        help="Generate queries and collect candidate web search results.",
    )
    parser.add_argument(
        "--validate-sources",
        action="store_true",
        help="Generate queries, search the web, and classify candidate sources.",
    )
    parser.add_argument(
        "--read-pages",
        action="store_true",
        help="Validate sources, read accepted/review pages, clean text, and cache content.",
    )
    parser.add_argument(
        "--extract-scholarships",
        action="store_true",
        help="Read pages and extract structured scholarship records with the LLM.",
    )
    parser.add_argument(
        "--save-knowledge-base",
        action="store_true",
        help="Extract scholarships and persist profile, queries, sources, and results to SQLite.",
    )
    parser.add_argument(
        "--match-scholarships",
        action="store_true",
        help="Extract scholarships and compare them against the normalized profile.",
    )
    parser.add_argument(
        "--rank-scholarships",
        action="store_true",
        help="Match scholarships and produce ranked recommendations.",
    )
    parser.add_argument(
        "--retrieve-known",
        action="store_true",
        help="Retrieve already-known scholarships from the local SQLite knowledge base.",
    )
    parser.add_argument(
        "--refresh-known",
        action="store_true",
        help="Refresh known scholarships from the local SQLite knowledge base.",
    )
    return parser.parse_args()


def run_llm_test() -> int:
    try:
        logger.info("Starting local LLM connection test")
        logger.info("Loading test prompt from %s", TEST_PROMPT_PATH)
        prompt = TEST_PROMPT_PATH.read_text(encoding="utf-8").strip()

        logger.info(
            "Calling provider '%s' with model '%s'",
            settings.LLM_PROVIDER,
            settings.OLLAMA_MODEL,
        )
        response = generate_text(prompt)

        print(response)
        logger.info("Local LLM connection test completed successfully")
        return 0
    except FileNotFoundError as exc:
        logger.error("Test prompt file not found: %s", exc)
    except LLMProviderError as exc:
        logger.error("%s", exc)
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected error: %s", exc)

    return 1


def main() -> int:
    args = parse_args()
    if args.test_llm:
        return run_llm_test()

    try:
        if args.refresh_known:
            logger.info("Starting Phase 13 refresh and scalability")
            refresh_payload = RefreshService().refresh()
            refresh_summary = refresh_payload["summary"]
            refresh_results = refresh_payload["refresh_results"]
            print(
                "Refresh summary: "
                f"records_checked={refresh_summary['records_checked']}, "
                f"kept_active={refresh_summary['kept_active']}, "
                f"marked_closed={refresh_summary['marked_closed']}, "
                f"marked_expired={refresh_summary['marked_expired']}, "
                f"skipped_recent={refresh_summary['skipped_recent']}, "
                f"skipped_closed={refresh_summary['skipped_closed']}, "
                f"errors={len(refresh_summary['errors'])}"
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = settings.RESULTS_DIR / f"refresh_result_{timestamp}.json"
            output_payload = build_refresh_output_payload(
                refresh_results=refresh_results,
                refresh_summary=refresh_summary,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Refresh output exported to %s", output_path)
            logger.info("Phase 13 refresh completed successfully")
            return 0

        profile_path = Path(args.profile)

        if args.rank_scholarships:
            logger.info("Starting Phase 12 ranking and recommendation")
        elif args.retrieve_known:
            logger.info("Starting Phase 10 retrieval from local knowledge base")
        elif args.match_scholarships:
            logger.info("Starting Phase 11 eligibility and matching")
        elif args.save_knowledge_base:
            logger.info("Starting Phase 9 scholarship knowledge base")
        elif args.extract_scholarships:
            logger.info("Starting Phase 8 scholarship extraction")
        elif args.read_pages:
            logger.info("Starting Phase 7 page reading and cleaning")
        elif args.validate_sources:
            logger.info("Starting Phase 6 source validation")
        elif args.search_web:
            logger.info("Starting Phase 5 web search")
        elif args.generate_queries:
            logger.info("Starting Phase 4 query generation")
        else:
            logger.info("Starting Phase 3 profile preparation")
        logger.info("Loading raw profile from %s", profile_path)
        raw_profile_data = load_json(profile_path)

        logger.info("Validating required profile fields")
        validate_profile(raw_profile_data)

        logger.info("Normalizing profile fields")
        normalized_profile = profile_agent.prepare_profile(raw_profile_data)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if args.retrieve_known:
            logger.info("Retrieving known scholarships from SQLite knowledge base")
            retrieval_payload = run_retrieval(normalized_profile)
            retrieval_summary = retrieval_payload["summary"]
            retrieval_results = retrieval_payload["retrieval_results"]
            print(
                "Retrieval summary: "
                f"retrieval_enabled={retrieval_summary['retrieval_enabled']}, "
                f"retrieved_count={retrieval_summary['retrieved_count']}, "
                f"usable_results={retrieval_summary['usable_results']}, "
                f"skipped_closed_or_expired={retrieval_summary['skipped_closed_or_expired']}, "
                f"errors={len(retrieval_summary['errors'])}"
            )

            output_path = settings.RESULTS_DIR / f"retrieval_result_{timestamp}.json"
            output_payload = build_retrieval_output_payload(
                normalized_profile=normalized_profile,
                retrieval_results=retrieval_results,
                retrieval_summary=retrieval_summary,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Retrieval output exported to %s", output_path)
            logger.info("Phase 10 retrieval completed successfully")
            return 0

        if args.rank_scholarships:
            logger.info("Generating scholarship search queries")
            queries = query_agent.generate_queries(normalized_profile)
            logger.info("Executing web search across %s generated queries", len(queries))
            candidate_results = search_agent.search(queries)
            logger.info("Validating %s candidate sources", len(candidate_results))
            validated_sources = source_validator_agent.validate_sources(
                candidate_results
            )
            logger.info("Reading and cleaning eligible pages")
            page_results = page_reader_agent.read_pages(validated_sources)
            page_results = enrich_page_results_with_source_metadata(
                page_results, validated_sources
            )
            logger.info("Extracting scholarships from cleaned page text")
            scholarships = extraction_agent.extract_scholarships(page_results)
            logger.info("Matching scholarships against the normalized profile")
            matching_payload = run_matching(normalized_profile, scholarships)
            matching_summary = matching_payload["summary"]
            matching_results = matching_payload["matching_results"]
            logger.info("Ranking scholarship recommendations")
            ranking_payload = run_ranking(matching_results)
            ranking_summary = ranking_payload["summary"]
            ranked_results = ranking_payload["ranked_results"]
            print(
                "Ranking summary: "
                f"total_evaluated={ranking_summary['total_evaluated']}, "
                f"total_ranked={ranking_summary['total_ranked']}, "
                f"high_priority={ranking_summary['high_priority']}, "
                f"medium_priority={ranking_summary['medium_priority']}, "
                f"low_priority={ranking_summary['low_priority']}, "
                f"not_recommended={ranking_summary['not_recommended']}, "
                f"errors={len(ranking_summary['errors'])}"
            )

            output_path = settings.RESULTS_DIR / f"ranking_result_{timestamp}.json"
            output_payload = build_ranking_output_payload(
                normalized_profile=normalized_profile,
                queries=queries,
                validated_sources=validated_sources,
                scholarships=scholarships,
                matching_results=matching_results,
                matching_summary=matching_summary,
                ranked_results=ranked_results,
                ranking_summary=ranking_summary,
                extraction_errors=extraction_agent.extraction_errors,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Ranking output exported to %s", output_path)
            logger.info("Phase 12 ranking and recommendation completed successfully")
            return 0

        if args.match_scholarships:
            logger.info("Generating scholarship search queries")
            queries = query_agent.generate_queries(normalized_profile)
            logger.info("Executing web search across %s generated queries", len(queries))
            candidate_results = search_agent.search(queries)
            logger.info("Validating %s candidate sources", len(candidate_results))
            validated_sources = source_validator_agent.validate_sources(
                candidate_results
            )
            logger.info("Reading and cleaning eligible pages")
            page_results = page_reader_agent.read_pages(validated_sources)
            page_results = enrich_page_results_with_source_metadata(
                page_results, validated_sources
            )
            logger.info("Extracting scholarships from cleaned page text")
            scholarships = extraction_agent.extract_scholarships(page_results)
            logger.info("Matching scholarships against the normalized profile")
            matching_payload = run_matching(normalized_profile, scholarships)
            matching_summary = matching_payload["summary"]
            matching_results = matching_payload["matching_results"]
            print(
                "Matching summary: "
                f"strong_matches={matching_summary['strong_matches']}, "
                f"possible_matches={matching_summary['possible_matches']}, "
                f"weak_matches={matching_summary['weak_matches']}, "
                f"not_eligible={matching_summary['not_eligible']}, "
                f"insufficient_information={matching_summary['insufficient_information']}, "
                f"errors={len(matching_summary['errors'])}"
            )

            output_path = settings.RESULTS_DIR / f"matching_result_{timestamp}.json"
            output_payload = build_matching_output_payload(
                normalized_profile=normalized_profile,
                queries=queries,
                validated_sources=validated_sources,
                scholarships=scholarships,
                matching_results=matching_results,
                matching_summary=matching_summary,
                extraction_errors=extraction_agent.extraction_errors,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Matching output exported to %s", output_path)
            logger.info("Phase 11 eligibility and matching completed successfully")
            return 0

        if args.save_knowledge_base:
            logger.info("Generating scholarship search queries")
            queries = query_agent.generate_queries(normalized_profile)
            logger.info("Executing web search across %s generated queries", len(queries))
            candidate_results = search_agent.search(queries)
            logger.info("Validating %s candidate sources", len(candidate_results))
            validated_sources = source_validator_agent.validate_sources(
                candidate_results
            )
            logger.info("Reading and cleaning eligible pages")
            page_results = page_reader_agent.read_pages(validated_sources)
            page_results = enrich_page_results_with_source_metadata(
                page_results, validated_sources
            )
            logger.info("Extracting scholarships from cleaned page text")
            scholarships = extraction_agent.extract_scholarships(page_results)
            logger.info("Saving pipeline results to SQLite knowledge base")
            save_summary = save_to_knowledge_base(
                normalized_profile=normalized_profile,
                queries=queries,
                validated_sources=validated_sources,
                extracted_scholarships=scholarships,
                extraction_errors=extraction_agent.extraction_errors,
            )
            print(
                "Knowledge base save: "
                f"profiles_saved={save_summary['profiles_saved']}, "
                f"queries_saved={save_summary['queries_saved']}, "
                f"sources_saved={save_summary['sources_saved']}, "
                f"scholarships_inserted={save_summary['scholarships_inserted']}, "
                f"scholarships_updated={save_summary['scholarships_updated']}, "
                f"errors={len(save_summary['errors'])}"
            )

            output_path = settings.RESULTS_DIR / f"knowledge_base_result_{timestamp}.json"
            output_payload = build_knowledge_base_output_payload(
                normalized_profile=normalized_profile,
                queries=queries,
                validated_sources=validated_sources,
                scholarships=scholarships,
                extraction_errors=extraction_agent.extraction_errors,
                save_summary=save_summary,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Knowledge base output exported to %s", output_path)
            logger.info("Phase 9 scholarship knowledge base completed successfully")
            return 0

        if args.extract_scholarships:
            logger.info("Generating scholarship search queries")
            queries = query_agent.generate_queries(normalized_profile)
            logger.info("Executing web search across %s generated queries", len(queries))
            candidate_results = search_agent.search(queries)
            logger.info("Validating %s candidate sources", len(candidate_results))
            validated_sources = source_validator_agent.validate_sources(
                candidate_results
            )
            logger.info("Reading and cleaning eligible pages")
            page_results = page_reader_agent.read_pages(validated_sources)
            page_results = enrich_page_results_with_source_metadata(
                page_results, validated_sources
            )
            logger.info("Extracting scholarships from cleaned page text")
            scholarships = extraction_agent.extract_scholarships(page_results)
            print(
                "Extraction results: "
                f"scholarships={len(scholarships)}, "
                f"errors={len(extraction_agent.extraction_errors)}"
            )

            output_path = settings.RESULTS_DIR / f"extraction_result_{timestamp}.json"
            output_payload = build_extraction_output_payload(
                normalized_profile=normalized_profile,
                queries=queries,
                candidate_results=candidate_results,
                validated_sources=validated_sources,
                page_results=page_results,
                scholarships=scholarships,
                extraction_errors=extraction_agent.extraction_errors,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Extraction output exported to %s", output_path)
            logger.info("Phase 8 scholarship extraction completed successfully")
            return 0

        if args.read_pages:
            logger.info("Generating scholarship search queries")
            queries = query_agent.generate_queries(normalized_profile)
            logger.info("Executing web search across %s generated queries", len(queries))
            candidate_results = search_agent.search(queries)
            logger.info("Validating %s candidate sources", len(candidate_results))
            validated_sources = source_validator_agent.validate_sources(
                candidate_results
            )
            logger.info("Reading and cleaning eligible pages")
            page_results = page_reader_agent.read_pages(validated_sources)
            page_counts = count_page_statuses(page_results)
            print(
                "Page results: "
                + ", ".join(
                    f"{status}={count}" for status, count in sorted(page_counts.items())
                )
            )

            output_path = settings.RESULTS_DIR / f"page_result_{timestamp}.json"
            output_payload = build_page_output_payload(
                normalized_profile=normalized_profile,
                queries=queries,
                candidate_results=candidate_results,
                validated_sources=validated_sources,
                page_results=page_results,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Page reading output exported to %s", output_path)
            logger.info("Phase 7 page reading and cleaning completed successfully")
            return 0

        if args.validate_sources:
            logger.info("Generating scholarship search queries")
            queries = query_agent.generate_queries(normalized_profile)
            logger.info("Executing web search across %s generated queries", len(queries))
            candidate_results = search_agent.search(queries)
            logger.info("Validating %s candidate sources", len(candidate_results))
            validated_sources = source_validator_agent.validate_sources(
                candidate_results
            )
            source_counts = count_source_decisions(validated_sources)
            print(
                "Source decisions: "
                f"accept={source_counts['accept']}, "
                f"review={source_counts['review']}, "
                f"reject={source_counts['reject']}"
            )

            output_path = settings.RESULTS_DIR / f"source_result_{timestamp}.json"
            output_payload = build_source_validation_output_payload(
                normalized_profile=normalized_profile,
                queries=queries,
                candidate_results=candidate_results,
                validated_sources=validated_sources,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Source validation output exported to %s", output_path)
            logger.info("Phase 6 source validation completed successfully")
            return 0

        if args.search_web:
            logger.info("Generating scholarship search queries")
            queries = query_agent.generate_queries(normalized_profile)
            logger.info("Executing web search across %s generated queries", len(queries))
            candidate_results = search_agent.search(queries)
            for result in candidate_results:
                print(
                    f"[{result['target_country']}] {result['title']} | "
                    f"{result['url']}"
                )

            output_path = settings.RESULTS_DIR / f"search_result_{timestamp}.json"
            output_payload = build_search_output_payload(
                normalized_profile=normalized_profile,
                queries=queries,
                candidate_results=candidate_results,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Search output exported to %s", output_path)
            logger.info("Phase 5 web search completed successfully")
            return 0

        if args.generate_queries:
            logger.info("Generating scholarship search queries")
            queries = query_agent.generate_queries(normalized_profile)
            for query in queries:
                print(
                    f"{query['priority']}. [{query['target_country']}] "
                    f"{query['query']} - {query['reason']}"
                )

            output_path = settings.RESULTS_DIR / f"query_result_{timestamp}.json"
            output_payload = build_query_output_payload(
                normalized_profile=normalized_profile,
                queries=queries,
                profile_path=profile_path,
                output_path=output_path,
            )
            save_json(output_path, output_payload)
            logger.info("Query output exported to %s", output_path)
            logger.info("Phase 4 query generation completed successfully")
            return 0

        output_path = settings.RESULTS_DIR / f"profile_result_{timestamp}.json"

        logger.info("Preparing structured normalized output")
        output_payload = build_output_payload(
            profile=normalized_profile,
            profile_path=profile_path,
            output_path=output_path,
        )

        save_json(output_path, output_payload)
        logger.info("Result exported to %s", output_path)
        logger.info("Phase 3 profile preparation completed successfully")
        return 0
    except FileNotFoundError as exc:
        logger.error("Profile file not found: %s", exc)
    except (
        JsonHandlerError,
        MatchValidationError,
        ProfileValidationError,
        QueryGenerationError,
        RankingValidationError,
        RetrievalValidationError,
        RefreshValidationError,
    ) as exc:
        logger.error("%s", exc)
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected error: %s", exc)

    return 1


if __name__ == "__main__":
    sys.exit(main())
