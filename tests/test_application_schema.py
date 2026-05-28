from __future__ import annotations

import pytest

from schemas.application_schema import (
    ApplicationSchemaError,
    validate_analysis_payload,
    validate_fill_payload,
)


def test_validate_analysis_payload_minimal() -> None:
    raw = {
        "requires_letter_of_intent": True,
        "letter_type": "motivation",
        "scholarship_purpose": "Support STEM leaders.",
        "extracted_fields": [
            {
                "field_id": "email",
                "label": "Email",
                "field_type": "email",
                "required": True,
            }
        ],
        "confidence": 80,
    }
    out = validate_analysis_payload(raw)
    assert out["requires_letter_of_intent"] is True
    assert len(out["extracted_fields"]) == 1
    assert out["extracted_fields"][0]["field_id"] == "email"


def test_validate_fill_payload_strips_letter_when_not_required() -> None:
    analysis = {"requires_letter_of_intent": False}
    raw = {
        "filled_fields": [
            {
                "field_id": "name",
                "label": "Name",
                "suggested_value": "Ana",
                "confidence": 90,
            }
        ],
        "letter_of_intent": "Should be removed",
    }
    out = validate_fill_payload(raw, analysis)
    assert out["letter_of_intent"] is None
    assert out["filled_fields"][0]["suggested_value"] == "Ana"
    assert any("no envía" in w.lower() for w in out["warnings"])


def test_validate_analysis_rejects_non_object() -> None:
    with pytest.raises(ApplicationSchemaError):
        validate_analysis_payload([])  # type: ignore[arg-type]
