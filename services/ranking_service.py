from __future__ import annotations

from collections import Counter

from agent.ranking_agent import RankingAgent


def run_ranking(matching_results: list[dict]) -> dict:
    agent = RankingAgent()
    ranked_results = agent.rank_recommendations(matching_results)
    counts = Counter(
        result.get("priority_label", "not_recommended") for result in ranked_results
    )

    summary = {
        "total_evaluated": len(matching_results),
        "total_ranked": len(ranked_results),
        "high_priority": counts.get("high_priority", 0),
        "medium_priority": counts.get("medium_priority", 0),
        "low_priority": counts.get("low_priority", 0),
        "not_recommended": counts.get("not_recommended", 0),
        "errors": agent.ranking_errors,
    }

    return {
        "summary": summary,
        "ranked_results": ranked_results,
    }
