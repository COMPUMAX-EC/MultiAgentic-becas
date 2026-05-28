"""Heuristic extraction of HTML form fields to complement LLM analysis."""
from __future__ import annotations

import re
from html import unescape


_INPUT_RE = re.compile(
    r"<(input|select|textarea)\b([^>]*)(?:/>|>(.*?)</\1>)",
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(
    r'(\w+)\s*=\s*["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_LABEL_FOR_RE = re.compile(
    r'<label[^>]*\bfor\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</label>',
    re.IGNORECASE | re.DOTALL,
)


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", unescape(text or "")).strip()


def extract_form_hints(html: str, *, max_fields: int = 40) -> list[dict]:
    """Return lightweight field hints from raw HTML."""
    if not html:
        return []

    labels_by_id: dict[str, str] = {}
    for match in _LABEL_FOR_RE.finditer(html):
        field_id = match.group(1).strip()
        label = _strip_tags(match.group(2))
        if field_id and label:
            labels_by_id[field_id] = label

    hints: list[dict] = []
    seen: set[str] = set()

    for match in _INPUT_RE.finditer(html):
        tag = match.group(1).lower()
        attrs_blob = match.group(2) or ""
        attrs = {k.lower(): v for k, v in _ATTR_RE.findall(attrs_blob)}
        field_type = attrs.get("type", tag).lower()
        if field_type in {"hidden", "submit", "button", "image", "reset"}:
            continue

        name = attrs.get("name") or attrs.get("id") or ""
        if not name or name in seen:
            continue
        seen.add(name)

        label = labels_by_id.get(attrs.get("id", ""), "") or attrs.get(
            "placeholder", ""
        ) or attrs.get("aria-label", "") or name.replace("_", " ").title()

        hints.append(
            {
                "field_id": name,
                "label": label[:120],
                "field_type": "textarea" if tag == "textarea" else field_type,
                "required": "required" in attrs_blob.lower(),
                "options": [],
                "description": "Detected in HTML form",
            }
        )
        if len(hints) >= max_fields:
            break

    return hints
