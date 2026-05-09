from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.source_validator_agent import SourceValidatorAgent
from api.server import is_policy_accepted_source
from database.repository import get_untrusted_source_match, save_untrusted_source


class SourceValidatorAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "sources.db"
        self.agent = SourceValidatorAgent(db_path=self.db_path)

    def test_official_university_source_accepted(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Computer Science Scholarships",
                "url": "https://www.example.edu/scholarships/computer-science",
                "snippet": "Scholarships and financial aid for international students.",
                "query": "computer science scholarships",
                "target_country": "United States",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "university")
        self.assertEqual(result["decision"], "accept")
        self.assertEqual(result["validation_status"], "accepted")
        self.assertEqual(result["source_domain"], "example.edu")

    def test_government_source_accepted(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Scholarships for International Students",
                "url": "https://www.scholarships.gov/programs",
                "snippet": "Government scholarship funding for students.",
                "query": "government scholarships",
                "target_country": "United States",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "government")
        self.assertEqual(result["decision"], "accept")
        self.assertEqual(result["validation_status"], "accepted")

    def test_embassy_source_accepted(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Embassy scholarship announcement",
                "url": "https://ca.usembassy.gov/education/scholarships/",
                "snippet": "Embassy scholarship funding for international students. Applications open.",
                "query": "embassy scholarships",
                "source_family": "embassy",
                "target_country": "Canada",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "embassy")
        self.assertEqual(result["validation_status"], "accepted")

    def test_international_organization_source_accepted(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "World Bank scholarship program",
                "url": "https://www.worldbank.org/en/programs/scholarships",
                "snippet": "World Bank scholarship funding for graduate students. Applications open.",
                "query": "international organization scholarships",
                "source_family": "international_organization",
                "target_country": "global",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "international_organization")
        self.assertEqual(result["validation_status"], "accepted")

    def test_foundation_source_accepted(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Foundation fellowship scholarships",
                "url": "https://www.fordfoundation.org/work/learning/fellowships/",
                "snippet": "Foundation fellowship and scholarship support for students. Deadline listed.",
                "query": "foundation scholarships",
                "source_family": "foundation",
                "target_country": "global",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "recognized_foundation")
        self.assertEqual(result["validation_status"], "accepted")

    def test_company_source_accepted(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Google student fellowship scholarship",
                "url": "https://scholarships.google.com/students/fellowship",
                "snippet": "Official company fellowship and scholarship funding for students.",
                "query": "company scholarships",
                "source_family": "company",
                "target_country": "global",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "official_company")
        self.assertEqual(result["validation_status"], "accepted")

    def test_professional_association_source_accepted(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "IEEE Computer Society scholarship",
                "url": "https://www.computer.org/volunteering/awards/scholarships",
                "snippet": "Professional association scholarship award for computer science students.",
                "query": "professional association scholarships",
                "source_family": "professional_association",
                "target_country": "global",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "professional_association")
        self.assertEqual(result["validation_status"], "accepted")

    def test_verified_news_source_accepted_with_warning(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "New scholarship call opens for international students",
                "url": "https://www.reuters.com/world/scholarship-call-international-students",
                "snippet": "A verified news report says the scholarship applications are open for students.",
                "query": "verified scholarship news",
                "target_country": "Canada",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "verified_news")
        self.assertEqual(result["decision"], "review")
        self.assertEqual(result["validation_status"], "accepted_with_warning")
        self.assertTrue(
            any("informational source" in warning for warning in result["warnings"])
        )
        self.assertIn(
            "Verified informational source; official call should be preferred if available.",
            result["warnings"],
        )
        self.assertTrue(is_policy_accepted_source(result))

    def test_generic_blog_rejected(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Top Scholarships You Should Know",
                "url": "https://medium.com/scholarship-blog/top-scholarships",
                "snippet": "A blog post listing scholarships for international students.",
                "query": "scholarships",
                "target_country": "Canada",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "generic_blog")
        self.assertEqual(result["decision"], "reject")
        self.assertEqual(result["validation_status"], "rejected")

    def test_low_authority_aggregator_rejected_by_policy_type(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Fully Funded Scholarships for Computer Science",
                "url": "https://fullyfundedscholarship.org/fully-funded-scholarships-computer-science/",
                "snippet": "A copied scholarship listing for international students.",
                "query": "computer science scholarships",
                "target_country": "Germany",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "copied_aggregator")
        self.assertEqual(result["decision"], "reject")
        stored = get_untrusted_source_match(
            result["url"],
            result["source_domain"],
            db_path=self.db_path,
        )
        self.assertIsNotNone(stored)

    def test_unknown_deadline_adds_warning_without_rejection(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Computer Science Scholarships",
                "url": "https://www.example.edu/scholarships/computer-science",
                "snippet": "Scholarships and financial aid for international students.",
                "query": "computer science scholarships",
                "target_country": "United States",
                "priority": 1,
            }
        )

        self.assertEqual(result["validation_status"], "accepted")
        self.assertIn("Deadline could not be verified.", result["warnings"])

    def test_expired_or_closed_source_rejected(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Applications closed for 2024 scholarship",
                "url": "https://www.example.edu/scholarships/closed",
                "snippet": "The deadline passed and applications closed.",
                "query": "scholarships",
                "target_country": "Canada",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "expired_or_closed")
        self.assertEqual(result["decision"], "reject")
        self.assertEqual(result["validation_status"], "rejected")

    def test_unrelated_source_rejected(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Campus cafeteria menu",
                "url": "https://www.example.edu/dining/menu",
                "snippet": "Weekly lunch and dinner options for students.",
                "query": "computer science scholarships",
                "target_country": "Canada",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "non_scholarship_page")
        self.assertEqual(result["decision"], "reject")

    def test_malformed_url_rejected_safely(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Scholarship result",
                "url": "not-a-url",
                "snippet": "Scholarship funding for students.",
                "query": "scholarships",
                "target_country": "Canada",
                "priority": 1,
            }
        )

        self.assertEqual(result["source_type"], "spam")
        self.assertEqual(result["decision"], "reject")

    def test_validated_source_preserves_metadata(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Scholarship Result",
                "url": "https://www.example.edu/scholarships/result",
                "snippet": "Scholarship funding for international students.",
                "source": "duckduckgo",
                "query": "original query",
                "query_used": "fallback query",
                "target_country": "Canada",
                "priority": 2,
            }
        )

        self.assertEqual(result["title"], "Scholarship Result")
        self.assertEqual(result["url"], "https://www.example.edu/scholarships/result")
        self.assertEqual(result["source"], "duckduckgo")
        self.assertEqual(result["query_used"], "fallback query")
        self.assertEqual(result["source_url"], "https://www.example.edu/scholarships/result")
        self.assertIn("validation_reason", result)
        self.assertIsInstance(result["warnings"], list)

    def test_validated_source_preserves_prompt_2_metadata(self) -> None:
        result = self.agent.validate_source(
            {
                "title": "Scholarship Result",
                "url": "https://www.example.edu/scholarships/result",
                "snippet": "Scholarship funding for international students.",
                "source": "duckduckgo",
                "query": "original query",
                "query_used": "fallback query",
                "query_family": "university",
                "source_family": "university",
                "source_domain": "example.edu",
                "target_country": "Canada",
                "priority": 2,
            }
        )

        self.assertEqual(result["query_family"], "university")
        self.assertEqual(result["source_family"], "university")
        self.assertEqual(result["source_domain"], "example.edu")

    def test_known_untrusted_source_rejected_before_classification(self) -> None:
        save_untrusted_source(
            "https://bad.example/scholarships",
            "bad.example",
            "generic blog",
            "generic_blog",
            db_path=self.db_path,
        )

        result = self.agent.validate_source(
            {
                "title": "Scholarship funding",
                "url": "https://bad.example/new-scholarship",
                "snippet": "Scholarship funding for students. Applications open.",
                "query": "scholarships",
                "target_country": "Canada",
                "priority": 1,
            }
        )

        self.assertEqual(result["validation_status"], "rejected")
        self.assertEqual(result["validation_reason"], "known_untrusted_source")
        self.assertIn("known_untrusted_source", result["risk_flags"])


if __name__ == "__main__":
    unittest.main()
