from __future__ import annotations

from collections import Counter

from agent.matching_agent import MatchingAgent


def run_matching(normalized_profile: dict, scholarships: list[dict]) -> dict:
    agent = MatchingAgent()
    matching_results = agent.match_scholarships(normalized_profile, scholarships)
    counts = Counter(
        result.get("eligibility_decision", "insufficient_information")
        for result in matching_results
    )

    summary = {
        "scholarships_evaluated": len(scholarships),
        "strong_matches": counts.get("strong_match", 0),
        "possible_matches": counts.get("possible_match", 0),
        "weak_matches": counts.get("weak_match", 0),
        "not_eligible": counts.get("not_eligible", 0),
        "insufficient_information": counts.get("insufficient_information", 0),
        "errors": agent.matching_errors,
    }

    return {
        "summary": summary,
        "matching_results": matching_results,
    }
