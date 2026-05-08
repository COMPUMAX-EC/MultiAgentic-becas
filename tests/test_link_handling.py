import unittest

from api.server import (
    build_display_link,
    dedupe_scholarships_by_best_link,
    normalize_recommendation_list,
)
from schemas.scholarship_schema import validate_scholarship_extractions


class UsefulLinkHandlingTests(unittest.TestCase):
    def test_official_link_has_priority(self) -> None:
        self.assertEqual(
            build_display_link(
                {
                    "official_link": "https://official.example.edu/scholarship",
                    "source_url": "https://source.example.edu/article",
                }
            ),
            "https://official.example.edu/scholarship",
        )

    def test_application_link_falls_back_before_source(self) -> None:
        self.assertEqual(
            build_display_link(
                {
                    "application_url": "https://apply.example.edu/form",
                    "source_url": "https://source.example.edu/scholarship",
                }
            ),
            "https://apply.example.edu/form",
        )

    def test_source_url_fallback_and_missing_scheme_normalization(self) -> None:
        self.assertEqual(
            build_display_link({"source_url": "www.example.edu/scholarship"}),
            "https://www.example.edu/scholarship",
        )

    def test_pdf_url_fallback(self) -> None:
        self.assertEqual(
            build_display_link({"pdf_url": "https://example.gov/call.pdf"}),
            "https://example.gov/call.pdf",
        )

    def test_no_useful_link_is_excluded_from_final_visible_results(self) -> None:
        records = normalize_recommendation_list(
            [
                {
                    "scholarship_name": "Untraceable Scholarship",
                    "final_score": 88,
                    "compatibility_score": 80,
                    "eligibility_decision": "possible_match",
                    "priority_label": "medium_priority",
                }
            ]
        )

        self.assertEqual(records, [])

    def test_malformed_links_are_not_used(self) -> None:
        self.assertEqual(
            build_display_link(
                {
                    "official_link": "javascript:alert(1)",
                    "application_url": "mailto:apply@example.edu",
                    "source_url": "https://source.example.edu/scholarship",
                }
            ),
            "https://source.example.edu/scholarship",
        )
        self.assertEqual(
            build_display_link({"source_url": "javascript:alert(1)", "pdf_url": ""}),
            "",
        )

    def test_extraction_validation_preserves_source_url_as_display_link(self) -> None:
        scholarships = validate_scholarship_extractions(
            [
                {
                    "scholarship_name": "Traceable Scholarship",
                    "extraction_confidence": 85,
                    "application_status": "open",
                }
            ],
            {
                "source_url": "https://source.example.edu/scholarship",
                "url": "https://source.example.edu/scholarship",
            },
        )

        self.assertEqual(
            scholarships[0]["source_url"], "https://source.example.edu/scholarship"
        )
        self.assertEqual(
            scholarships[0]["display_link"],
            "https://source.example.edu/scholarship",
        )

    def test_dedupe_keeps_better_linked_duplicate(self) -> None:
        deduped = dedupe_scholarships_by_best_link(
            [
                {
                    "scholarship_name": "Example Scholarship",
                    "source_url": "https://source.example.edu/scholarship",
                },
                {
                    "scholarship_name": "Example Scholarship",
                    "source_url": "https://source.example.edu/scholarship",
                    "official_link": "https://official.example.edu/scholarship",
                },
            ]
        )

        self.assertEqual(len(deduped), 1)
        self.assertEqual(
            deduped[0]["official_link"], "https://official.example.edu/scholarship"
        )


if __name__ == "__main__":
    unittest.main()
