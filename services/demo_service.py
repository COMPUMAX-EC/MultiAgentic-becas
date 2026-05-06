from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agent.extraction_agent import ExtractionAgent
from agent.page_reader_agent import PageReaderAgent
from agent.profile_agent import ProfileAgent
from agent.query_agent import QueryAgent
from agent.search_agent import SearchAgent
from agent.source_validator_agent import SourceValidatorAgent
from config.settings import settings
from schemas.demo_schema import build_demo_output, build_workflow_step
from schemas.profile_schema import validate_profile
from services.matching_service import run_matching
from services.ranking_service import run_ranking
from utils.json_handler import load_json, save_json
from utils.logger import get_logger


logger = get_logger(__name__)


class DemoService:
    def __init__(
        self,
        profile_agent: ProfileAgent | None = None,
        query_agent: QueryAgent | None = None,
        search_agent: SearchAgent | None = None,
        source_validator_agent: SourceValidatorAgent | None = None,
        page_reader_agent: PageReaderAgent | None = None,
        extraction_agent: ExtractionAgent | None = None,
        matching_runner=run_matching,
        ranking_runner=run_ranking,
        load_json_fn=load_json,
        save_json_fn=save_json,
    ) -> None:
        self.profile_agent = profile_agent or ProfileAgent()
        self.query_agent = query_agent or QueryAgent()
        self.search_agent = search_agent or SearchAgent()
        self.source_validator_agent = source_validator_agent or SourceValidatorAgent()
        self.page_reader_agent = page_reader_agent or PageReaderAgent()
        self.extraction_agent = extraction_agent or ExtractionAgent()
        self.matching_runner = matching_runner
        self.ranking_runner = ranking_runner
        self.load_json = load_json_fn
        self.save_json = save_json_fn

    def run(self, profile_path: str | Path | None = None) -> dict:
        resolved_profile_path = Path(profile_path or settings.DEMO_PROFILE_PATH)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_output_path = settings.DEMO_OUTPUT_DIR / f"demo_result_{timestamp}.json"
        markdown_output_path = settings.DEMO_OUTPUT_DIR / f"demo_report_{timestamp}.md"

        workflow_steps: list[dict] = []
        errors: list[str] = []
        queries: list[dict] = []
        candidate_results: list[dict] = []
        validated_sources: list[dict] = []
        page_results: list[dict] = []
        scholarships: list[dict] = []
        matching_results: list[dict] = []
        ranked_results: list[dict] = []
        normalized_profile: dict = {}

        def add_step(step_name: str, status: str, count: int, message: str) -> None:
            workflow_steps.append(build_workflow_step(step_name, status, count, message))

        try:
            raw_profile = self.load_json(resolved_profile_path)
            validate_profile(raw_profile)
            normalized_profile = self.profile_agent.prepare_profile(raw_profile)
            add_step(
                "profile_normalization",
                "completed",
                1,
                "Demo profile loaded and normalized successfully.",
            )
        except Exception as exc:
            errors.append(f"profile_normalization: {exc}")
            add_step(
                "profile_normalization",
                "failed",
                0,
                f"Demo profile could not be prepared: {exc}",
            )
            return self._finalize_output(
                normalized_profile=normalized_profile,
                workflow_steps=workflow_steps,
                queries=queries,
                candidate_results=candidate_results,
                validated_sources=validated_sources,
                page_results=page_results,
                scholarships=scholarships,
                matching_results=matching_results,
                ranked_results=ranked_results,
                errors=errors,
                json_output_path=json_output_path,
                markdown_output_path=markdown_output_path,
            )

        pipeline_failed = False

        try:
            queries = self.query_agent.generate_queries(normalized_profile)
            add_step(
                "query_generation",
                "completed",
                len(queries),
                "Scholarship search queries generated.",
            )
        except Exception as exc:
            errors.append(f"query_generation: {exc}")
            add_step("query_generation", "failed", 0, f"Query generation failed: {exc}")
            pipeline_failed = True

        if not pipeline_failed:
            if settings.DEMO_USE_LIVE_SEARCH:
                try:
                    candidate_results = self.search_agent.search(queries)
                    add_step(
                        "web_search",
                        "completed",
                        len(candidate_results),
                        "Candidate scholarship sources collected from live search.",
                    )
                except Exception as exc:
                    errors.append(f"web_search: {exc}")
                    add_step("web_search", "failed", 0, f"Web search failed: {exc}")
                    pipeline_failed = True
            else:
                add_step(
                    "web_search",
                    "skipped",
                    0,
                    "Live search disabled for demo mode.",
                )
                pipeline_failed = True

        if not pipeline_failed:
            try:
                validated_sources = self.source_validator_agent.validate_sources(
                    candidate_results
                )
                add_step(
                    "source_validation",
                    "completed",
                    len(validated_sources),
                    "Candidate sources validated.",
                )
            except Exception as exc:
                errors.append(f"source_validation: {exc}")
                add_step(
                    "source_validation",
                    "failed",
                    0,
                    f"Source validation failed: {exc}",
                )
                pipeline_failed = True
        else:
            add_step(
                "source_validation",
                "skipped",
                0,
                "Skipped because a previous step failed.",
            )

        if not pipeline_failed:
            try:
                page_results = self.page_reader_agent.read_pages(validated_sources)
                add_step(
                    "page_reading",
                    "completed",
                    len(page_results),
                    "Eligible pages read and cleaned.",
                )
            except Exception as exc:
                errors.append(f"page_reading: {exc}")
                add_step("page_reading", "failed", 0, f"Page reading failed: {exc}")
                pipeline_failed = True
        else:
            add_step("page_reading", "skipped", 0, "Skipped because a previous step failed.")

        if not pipeline_failed:
            try:
                scholarships = self.extraction_agent.extract_scholarships(page_results)
                extraction_errors = getattr(self.extraction_agent, "extraction_errors", [])
                if extraction_errors:
                    errors.extend(f"extraction: {item.get('error')}" for item in extraction_errors)
                add_step(
                    "scholarship_extraction",
                    "completed" if scholarships else "partial",
                    len(scholarships),
                    "Structured scholarship records extracted.",
                )
            except Exception as exc:
                errors.append(f"scholarship_extraction: {exc}")
                add_step(
                    "scholarship_extraction",
                    "failed",
                    0,
                    f"Scholarship extraction failed: {exc}",
                )
                pipeline_failed = True
        else:
            add_step(
                "scholarship_extraction",
                "skipped",
                0,
                "Skipped because a previous step failed.",
            )

        if not pipeline_failed:
            try:
                matching_payload = self.matching_runner(normalized_profile, scholarships)
                matching_results = matching_payload["matching_results"]
                matching_errors = matching_payload["summary"].get("errors", [])
                if matching_errors:
                    errors.extend(f"matching: {item.get('error')}" for item in matching_errors)
                add_step(
                    "matching",
                    "completed",
                    len(matching_results),
                    "Extracted scholarships matched against the demo profile.",
                )
            except Exception as exc:
                errors.append(f"matching: {exc}")
                add_step("matching", "failed", 0, f"Matching failed: {exc}")
                pipeline_failed = True
        else:
            add_step("matching", "skipped", 0, "Skipped because a previous step failed.")

        if not pipeline_failed:
            try:
                ranking_payload = self.ranking_runner(matching_results)
                ranked_results = ranking_payload["ranked_results"][: settings.DEMO_MAX_RESULTS]
                ranking_errors = ranking_payload["summary"].get("errors", [])
                if ranking_errors:
                    errors.extend(f"ranking: {item.get('error')}" for item in ranking_errors)
                add_step(
                    "ranking",
                    "completed",
                    len(ranked_results),
                    "Final scholarship recommendations ranked for demo output.",
                )
            except Exception as exc:
                errors.append(f"ranking: {exc}")
                add_step("ranking", "failed", 0, f"Ranking failed: {exc}")
        else:
            add_step("ranking", "skipped", 0, "Skipped because a previous step failed.")

        return self._finalize_output(
            normalized_profile=normalized_profile,
            workflow_steps=workflow_steps,
            queries=queries,
            candidate_results=candidate_results,
            validated_sources=validated_sources,
            page_results=page_results,
            scholarships=scholarships,
            matching_results=matching_results,
            ranked_results=ranked_results,
            errors=errors,
            json_output_path=json_output_path,
            markdown_output_path=markdown_output_path,
        )

    def _finalize_output(
        self,
        normalized_profile: dict,
        workflow_steps: list[dict],
        queries: list[dict],
        candidate_results: list[dict],
        validated_sources: list[dict],
        page_results: list[dict],
        scholarships: list[dict],
        matching_results: list[dict],
        ranked_results: list[dict],
        errors: list[str],
        json_output_path: Path,
        markdown_output_path: Path,
    ) -> dict:
        cleaned_errors = self._deduplicate_items(errors)
        top_recommendations = [
            {
                "rank": recommendation.get("rank"),
                "scholarship_name": recommendation.get("scholarship_name"),
                "final_score": recommendation.get("final_score"),
                "compatibility_score": recommendation.get("compatibility_score"),
                "eligibility_decision": recommendation.get("eligibility_decision"),
                "priority_label": recommendation.get("priority_label"),
                "recommendation_summary": recommendation.get("recommendation_summary"),
                "ranking_reasons": recommendation.get("ranking_reasons", []),
                "source_url": recommendation.get("source_url"),
            }
            for recommendation in ranked_results[: settings.DEMO_MAX_RESULTS]
        ]

        profile_summary = {
            "nationality": normalized_profile.get("nationality"),
            "academic_level": normalized_profile.get("academic_level"),
            "field_of_study": normalized_profile.get("field_of_study"),
            "target_countries": normalized_profile.get("target_countries", []),
        }
        demo_status = "success"
        if cleaned_errors and ranked_results:
            demo_status = "partial_failure"
        elif cleaned_errors:
            demo_status = "failed"

        output_files = {
            "json": str(json_output_path),
            "markdown": str(markdown_output_path),
        }
        demo_output = build_demo_output(
            demo_status=demo_status,
            profile_summary=profile_summary,
            workflow_steps=workflow_steps,
            generated_queries_count=len(queries),
            sources_found_count=len(candidate_results),
            sources_validated_count=len(validated_sources),
            pages_read_count=len(page_results),
            scholarships_extracted_count=len(scholarships),
            matches_count=len(matching_results),
            ranked_results_count=len(ranked_results),
            top_recommendations=top_recommendations,
            errors=cleaned_errors,
            output_files=output_files,
        )

        self.save_json(json_output_path, demo_output)
        markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_output_path.write_text(
            self._build_markdown_report(demo_output),
            encoding="utf-8",
        )
        return demo_output

    def _build_markdown_report(self, demo_output: dict) -> str:
        lines = [
            "# Hackathon Technical Demo",
            "",
            f"- Status: {demo_output['demo_status']}",
            f"- Nationality: {demo_output['profile_summary'].get('nationality', 'Unknown')}",
            f"- Academic level: {demo_output['profile_summary'].get('academic_level', 'Unknown')}",
            f"- Field of study: {demo_output['profile_summary'].get('field_of_study', 'Unknown')}",
            "- Target countries: "
            + ", ".join(demo_output["profile_summary"].get("target_countries", [])),
            f"- Queries: {demo_output['generated_queries_count']}",
            f"- Sources found: {demo_output['sources_found_count']}",
            f"- Sources validated: {demo_output['sources_validated_count']}",
            f"- Pages read: {demo_output['pages_read_count']}",
            f"- Scholarships extracted: {demo_output['scholarships_extracted_count']}",
            f"- Matches: {demo_output['matches_count']}",
            f"- Ranked results: {demo_output['ranked_results_count']}",
            "",
            "## Workflow Steps",
            "",
        ]

        for step in demo_output["workflow_steps"]:
            lines.append(
                f"- {step['step_name']}: {step['status']} ({step['count']}) - {step['message']}"
            )

        lines.extend(["", "## Top Recommendations", ""])
        if demo_output["top_recommendations"]:
            for recommendation in demo_output["top_recommendations"]:
                lines.append(
                    f"- #{recommendation.get('rank')} {recommendation.get('scholarship_name')} "
                    f"({recommendation.get('priority_label')}, "
                    f"score={recommendation.get('final_score')}, "
                    f"eligibility={recommendation.get('eligibility_decision')})"
                )
                lines.append(
                    f"  - Summary: {recommendation.get('recommendation_summary')}"
                )
                lines.append(f"  - Link: {recommendation.get('source_url')}")
        else:
            lines.append("- No ranked recommendations available.")

        if demo_output["errors"]:
            lines.extend(["", "## Errors", ""])
            for error in demo_output["errors"]:
                lines.append(f"- {error}")

        return "\n".join(lines) + "\n"

    def _deduplicate_items(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned_values: list[str] = []

        for value in values:
            cleaned_value = str(value).strip()
            if not cleaned_value:
                continue
            comparison_key = cleaned_value.casefold()
            if comparison_key in seen:
                continue
            seen.add(comparison_key)
            cleaned_values.append(cleaned_value)

        return cleaned_values
