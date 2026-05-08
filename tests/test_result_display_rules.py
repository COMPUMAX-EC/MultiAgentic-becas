import unittest

from api.server import (
    build_display_link,
    normalize_recommendation_list,
    split_recommendations,
)


class ResultDisplayRulesTests(unittest.TestCase):
    def test_recommended_results_are_not_capped(self) -> None:
        recommended, less_recommended = split_recommendations(
            [
                self._result(f"Recommended {index}", "high_priority", 90 - index)
                for index in range(15)
            ]
        )

        self.assertEqual(len(recommended), 15)
        self.assertEqual(less_recommended, [])

    def test_less_recommended_results_are_capped_at_ten(self) -> None:
        recommended, less_recommended = split_recommendations(
            [self._result("Top", "high_priority", 95)]
            + [
                self._result(f"Less {index}", "low_priority", 44 - index)
                for index in range(25)
            ]
        )

        self.assertEqual(len(recommended), 1)
        self.assertEqual(len(less_recommended), 10)

    def test_mixed_labels_split_correctly(self) -> None:
        recommended, less_recommended = split_recommendations(
            [
                self._result("High", "high_priority", 90),
                self._result("Medium", "medium_priority", 70),
                self._result("Possible", "possible_match", 55),
                self._result("Low", "low_priority", 40),
                self._result("Unclear", "insufficient_information", 35),
                self._result("No", "not_recommended", 20),
            ]
        )

        self.assertEqual(
            [result["scholarship_name"] for result in recommended],
            ["High", "Medium", "Possible"],
        )
        self.assertEqual(
            [result["scholarship_name"] for result in less_recommended],
            ["Low", "Unclear", "No"],
        )

    def test_sections_sort_by_score_compatibility_then_rank(self) -> None:
        recommended, _ = split_recommendations(
            [
                self._result("Third", "high_priority", 80, compatibility=90, rank=3),
                self._result("First", "high_priority", 90, compatibility=70, rank=2),
                self._result("Second", "high_priority", 80, compatibility=90, rank=1),
            ]
        )

        self.assertEqual(
            [result["scholarship_name"] for result in recommended],
            ["First", "Second", "Third"],
        )

    def test_link_fallback_uses_source_url(self) -> None:
        self.assertEqual(
            build_display_link({"source_url": "https://example.edu/source"}),
            "https://example.edu/source",
        )

    def test_no_link_is_excluded_safely(self) -> None:
        records = normalize_recommendation_list(
            [
                {
                    "scholarship_name": "No Link",
                    "priority_label": "high_priority",
                    "final_score": 95,
                    "compatibility_score": 90,
                }
            ]
        )

        self.assertEqual(records, [])

    def _result(
        self,
        name: str,
        priority_label: str,
        final_score: int,
        compatibility: int = 70,
        rank: int = 1,
    ) -> dict:
        return {
            "rank": rank,
            "scholarship_name": name,
            "priority_label": priority_label,
            "final_score": final_score,
            "compatibility_score": compatibility,
            "source_url": f"https://example.edu/{name.lower().replace(' ', '-')}",
            "display_link": f"https://example.edu/{name.lower().replace(' ', '-')}",
        }


if __name__ == "__main__":
    unittest.main()
