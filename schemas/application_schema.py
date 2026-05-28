"""Validation for scholarship application assistant output."""
from __future__ import annotations

from typing import Any


class ApplicationSchemaError(ValueError):
    pass


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _as_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def validate_analysis_payload(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ApplicationSchemaError("Analysis payload must be a JSON object.")

    fields = []
    for entry in _as_list(raw.get("extracted_fields")):
        if not isinstance(entry, dict):
            continue
        field_id = _as_str(entry.get("field_id") or entry.get("label"))
        if not field_id:
            continue
        fields.append(
            {
                "field_id": field_id,
                "label": _as_str(entry.get("label"), field_id),
                "field_type": _as_str(entry.get("field_type"), "text").lower(),
                "required": bool(entry.get("required", False)),
                "options": [
                    _as_str(o) for o in _as_list(entry.get("options")) if _as_str(o)
                ],
                "description": _as_str(entry.get("description")),
            }
        )

    letter_type = _as_str(raw.get("letter_type"), "none").lower()
    requires_letter = bool(raw.get("requires_letter_of_intent")) or letter_type not in {
        "",
        "none",
        "null",
    }

    return {
        "requires_letter_of_intent": requires_letter,
        "letter_type": letter_type if requires_letter else "none",
        "letter_language": _as_str(raw.get("letter_language"), "es").lower()[:2],
        "scholarship_purpose": _as_str(raw.get("scholarship_purpose")),
        "extracted_fields": fields,
        "submission_notes": [
            _as_str(n) for n in _as_list(raw.get("submission_notes")) if _as_str(n)
        ],
        "confidence": max(0, min(100, int(raw.get("confidence", 50)))),
    }


def validate_fill_payload(raw: dict, analysis: dict) -> dict:
    if not isinstance(raw, dict):
        raise ApplicationSchemaError("Fill payload must be a JSON object.")

    filled = []
    for entry in _as_list(raw.get("filled_fields")):
        if not isinstance(entry, dict):
            continue
        field_id = _as_str(entry.get("field_id") or entry.get("label"))
        if not field_id:
            continue
        filled.append(
            {
                "field_id": field_id,
                "label": _as_str(entry.get("label"), field_id),
                "suggested_value": _as_str(entry.get("suggested_value")),
                "confidence": max(0, min(100, int(entry.get("confidence", 70)))),
                "notes": _as_str(entry.get("notes")),
            }
        )

    letter = raw.get("letter_of_intent")
    letter_text = _as_str(letter) if letter else None
    if not analysis.get("requires_letter_of_intent"):
        letter_text = None

    warnings = [
        _as_str(w)
        for w in _as_list(raw.get("warnings"))
        if _as_str(w)
    ]
    warnings.append(
        "Revisa y edita todo antes de enviar. Este asistente no envía el formulario automáticamente."
    )

    return {
        "filled_fields": filled,
        "letter_of_intent": letter_text,
        "submission_checklist": [
            _as_str(c) for c in _as_list(raw.get("submission_checklist")) if _as_str(c)
        ],
        "warnings": list(dict.fromkeys(warnings)),
    }
