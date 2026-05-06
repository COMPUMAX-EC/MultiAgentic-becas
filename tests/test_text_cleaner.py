from __future__ import annotations

import unittest

from tools.text_cleaner import clean_text


class TextCleanerTests(unittest.TestCase):
    def test_whitespace_normalization(self) -> None:
        cleaned_text = clean_text(" Scholarship    text \n\n\n with   spaces ")

        self.assertEqual(cleaned_text, "Scholarship text with spaces")

    def test_script_and_style_removal(self) -> None:
        cleaned_text = clean_text(
            """
            <html>
              <style>.hidden { display: none; }</style>
              <script>alert("noise")</script>
              <body><h1>Scholarship deadline</h1></body>
            </html>
            """
        )

        self.assertIn("Scholarship deadline", cleaned_text)
        self.assertNotIn("alert", cleaned_text)
        self.assertNotIn("display", cleaned_text)

    def test_max_character_truncation(self) -> None:
        cleaned_text = clean_text("abcdef", max_chars=3)

        self.assertEqual(cleaned_text, "abc")

    def test_empty_content_handling(self) -> None:
        self.assertEqual(clean_text("   "), "")


if __name__ == "__main__":
    unittest.main()
