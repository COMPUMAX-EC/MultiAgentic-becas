from __future__ import annotations

import unittest

from agent.source_validator_agent import SourceValidatorAgent


class SourceValidatorAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = SourceValidatorAgent()

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

        self.assertEqual(result["source_type"], "official_university")
        self.assertEqual(result["decision"], "accept")

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

        self.assertEqual(result["source_type"], "official_government")
        self.assertEqual(result["decision"], "accept")

    def test_blog_or_media_source_reviewed_or_rejected(self) -> None:
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

        self.assertEqual(result["source_type"], "blog_or_media")
        self.assertIn(result["decision"], {"review", "reject"})

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

        self.assertEqual(result["source_type"], "scholarship_database")
        self.assertIn(result["decision"], {"review", "reject"})

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

        self.assertEqual(result["source_type"], "irrelevant")
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

        self.assertEqual(result["source_type"], "spam_or_low_quality")
        self.assertEqual(result["decision"], "reject")


if __name__ == "__main__":
    unittest.main()
