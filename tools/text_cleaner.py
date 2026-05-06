from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

from config.settings import settings


NOISE_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "svg"}


class ReadableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in NOISE_TAGS:
            self._skip_depth += 1
            return
        if tag.lower() in {"p", "br", "li", "h1", "h2", "h3", "section", "div"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in NOISE_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag.lower() in {"p", "li", "h1", "h2", "h3", "section", "div"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned_data = data.strip()
        if cleaned_data:
            self._parts.append(cleaned_data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def clean_text(raw_content: str, max_chars: int | None = None) -> str:
    if not raw_content or not raw_content.strip():
        return ""

    parser = ReadableTextParser()
    parser.feed(raw_content)
    parsed_text = parser.get_text()
    if not parsed_text.strip():
        parsed_text = raw_content

    parsed_text = re.sub(r"(?is)<(script|style|nav|footer|header|noscript|svg).*?</\1>", " ", parsed_text)
    parsed_text = re.sub(r"(?s)<[^>]+>", " ", parsed_text)
    parsed_text = unescape(parsed_text)
    parsed_text = re.sub(r"\s+", " ", parsed_text).strip()

    limit = settings.PAGE_MAX_CHARS if max_chars is None else max_chars
    return parsed_text[:limit]
