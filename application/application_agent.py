"""
Application assistant — analyze forms, suggest field values, draft intent letters.

Does not auto-submit external portals; produces a reviewable application package.
"""
from __future__ import annotations

import json
from pathlib import Path

from application.form_hints import extract_form_hints
from config.settings import settings
from llm.provider import LLMProviderError, generate_text
from schemas.application_schema import (
    ApplicationSchemaError,
    validate_analysis_payload,
    validate_fill_payload,
)
from tools.page_reader import PageReadError, read_page
from tools.text_cleaner import clean_text
from utils.json_handler import JsonHandlerError, parse_json_text
from utils.url_utils import first_useful_url

ANALYZE_PROMPT_PATH = settings.PROJECT_ROOT / "prompts" / "application_analyze.txt"
FILL_PROMPT_PATH = settings.PROJECT_ROOT / "prompts" / "application_fill.txt"
PAGE_TEXT_LIMIT = min(settings.EXTRACTION_TEXT_MAX_CHARS, 14_000)


class ApplicationAgentError(RuntimeError):
    pass


class ApplicationAgent:
    def __init__(
        self,
        analyze_prompt_path: Path = ANALYZE_PROMPT_PATH,
        fill_prompt_path: Path = FILL_PROMPT_PATH,
    ) -> None:
        self.analyze_prompt = analyze_prompt_path.read_text(encoding="utf-8")
        self.fill_prompt = fill_prompt_path.read_text(encoding="utf-8")

    def prepare_application_package(
        self,
        *,
        profile: dict,
        scholarship: dict,
        applicant_name: str = "",
        applicant_email: str = "",
        application_url: str | None = None,
    ) -> dict:
        url = self._resolve_application_url(scholarship, application_url)
        page_context = self._load_page_context(url)
        analysis = self._analyze_form(scholarship, profile, page_context, url)
        fill_result = self._fill_application(
            scholarship,
            profile,
            analysis,
            applicant_name=applicant_name,
            applicant_email=applicant_email,
        )

        return {
            "scholarship_name": scholarship.get("scholarship_name")
            or scholarship.get("name")
            or "Beca",
            "institution": scholarship.get("institution", ""),
            "application_url": url or "",
            "page_status": page_context.get("status", "skipped"),
            "analysis": analysis,
            "filled_fields": fill_result["filled_fields"],
            "letter_of_intent": fill_result["letter_of_intent"],
            "submission_checklist": fill_result["submission_checklist"],
            "warnings": fill_result["warnings"],
            "manual_review_required": True,
        }

    def _resolve_application_url(
        self, scholarship: dict, override: str | None
    ) -> str | None:
        if override and override.strip():
            return override.strip()
        return first_useful_url(
            scholarship.get("application_url"),
            scholarship.get("official_link"),
            scholarship.get("source_url"),
            scholarship.get("url"),
        )

    def _load_page_context(self, url: str | None) -> dict:
        if not url:
            return {"status": "no_url", "cleaned_text": "", "form_hints": []}

        try:
            raw_html = read_page(url)
            cleaned = clean_text(raw_html)[:PAGE_TEXT_LIMIT]
            hints = extract_form_hints(raw_html)
            return {
                "status": "read_ok",
                "url": url,
                "cleaned_text": cleaned,
                "form_hints": hints,
            }
        except PageReadError as exc:
            return {
                "status": "read_failed",
                "url": url,
                "error": str(exc),
                "cleaned_text": "",
                "form_hints": [],
            }

    def _analyze_form(
        self,
        scholarship: dict,
        profile: dict,
        page_context: dict,
        url: str | None,
    ) -> dict:
        payload = {
            "scholarship": self._scholarship_summary(scholarship),
            "student_profile": profile,
            "application_url": url or "",
            "page_status": page_context.get("status"),
            "page_text": page_context.get("cleaned_text", ""),
            "html_form_hints": page_context.get("form_hints", []),
        }
        prompt = (
            f"{self.analyze_prompt}\n\n"
            f"Input:\n{json.dumps(payload, indent=2, ensure_ascii=False)}"
        )
        try:
            raw = generate_text(prompt)
            parsed = parse_json_text(raw)
            return validate_analysis_payload(parsed)
        except (LLMProviderError, JsonHandlerError, ApplicationSchemaError) as exc:
            return self._fallback_analysis(scholarship, profile, str(exc))

    def _fill_application(
        self,
        scholarship: dict,
        profile: dict,
        analysis: dict,
        *,
        applicant_name: str,
        applicant_email: str,
    ) -> dict:
        enriched_profile = {
            **profile,
            "applicant_name": applicant_name or profile.get("applicant_name", ""),
            "applicant_email": applicant_email or profile.get("applicant_email", ""),
        }
        payload = {
            "scholarship": self._scholarship_summary(scholarship),
            "student_profile": enriched_profile,
            "requires_letter_of_intent": analysis.get("requires_letter_of_intent"),
            "letter_type": analysis.get("letter_type"),
            "letter_language": analysis.get("letter_language", "es"),
            "scholarship_purpose": analysis.get("scholarship_purpose"),
            "extracted_fields": analysis.get("extracted_fields", []),
        }
        prompt = (
            f"{self.fill_prompt}\n\n"
            f"Input:\n{json.dumps(payload, indent=2, ensure_ascii=False)}"
        )
        try:
            raw = generate_text(prompt)
            parsed = parse_json_text(raw)
            return validate_fill_payload(parsed, analysis)
        except (LLMProviderError, JsonHandlerError, ApplicationSchemaError) as exc:
            return self._fallback_fill(analysis, enriched_profile, str(exc))

    def _scholarship_summary(self, scholarship: dict) -> dict:
        return {
            "name": scholarship.get("scholarship_name") or scholarship.get("name"),
            "institution": scholarship.get("institution"),
            "country": scholarship.get("country"),
            "academic_level": scholarship.get("academic_level"),
            "fields": scholarship.get("fields") or scholarship.get("fields_json"),
            "benefits": scholarship.get("benefits") or scholarship.get("benefits_json"),
            "requirements": scholarship.get("requirements")
            or scholarship.get("requirements_json"),
            "deadline": scholarship.get("deadline"),
            "application_status": scholarship.get("application_status"),
            "description": (scholarship.get("description") or "")[:2000],
        }

    def _fallback_analysis(
        self, scholarship: dict, profile: dict, error: str
    ) -> dict:
        fields = [
            {
                "field_id": "full_name",
                "label": "Nombre completo",
                "field_type": "text",
                "required": True,
                "options": [],
                "description": "Nombre del postulante",
            },
            {
                "field_id": "email",
                "label": "Correo electrónico",
                "field_type": "email",
                "required": True,
                "options": [],
                "description": "Email de contacto",
            },
            {
                "field_id": "nationality",
                "label": "Nacionalidad",
                "field_type": "text",
                "required": True,
                "options": [],
                "description": "",
            },
            {
                "field_id": "academic_level",
                "label": "Nivel académico",
                "field_type": "text",
                "required": True,
                "options": [],
                "description": "",
            },
            {
                "field_id": "field_of_study",
                "label": "Área de estudio",
                "field_type": "text",
                "required": True,
                "options": [],
                "description": "",
            },
            {
                "field_id": "motivation_statement",
                "label": "Carta / declaración de motivación",
                "field_type": "textarea",
                "required": True,
                "options": [],
                "description": "Carta alineada a la beca",
            },
        ]
        purpose = (
            f"La beca {scholarship.get('scholarship_name', '')} apoya estudios en "
            f"{scholarship.get('country', '')} para perfiles de "
            f"{scholarship.get('academic_level', '')} en "
            f"{scholarship.get('field_of_study', profile.get('field_of_study', ''))}."
        )
        return {
            "requires_letter_of_intent": True,
            "letter_type": "motivation",
            "letter_language": "es",
            "scholarship_purpose": purpose.strip(),
            "extracted_fields": fields,
            "submission_notes": [f"Análisis LLM no disponible: {error}"],
            "confidence": 40,
        }

    def _fallback_fill(
        self, analysis: dict, profile: dict, error: str
    ) -> dict:
        filled = []
        name = profile.get("applicant_name", "")
        email = profile.get("applicant_email", "")
        mapping = {
            "full_name": name,
            "email": email,
            "nationality": profile.get("nationality", ""),
            "country_of_residence": profile.get("country_of_residence", ""),
            "academic_level": profile.get("academic_level", ""),
            "field_of_study": profile.get("field_of_study", ""),
            "target_countries": profile.get("target_countries", ""),
            "languages": profile.get("languages", ""),
            "interests": profile.get("interests", ""),
        }
        for field in analysis.get("extracted_fields", []):
            fid = field.get("field_id", "")
            filled.append(
                {
                    "field_id": fid,
                    "label": field.get("label", fid),
                    "suggested_value": str(mapping.get(fid, "")),
                    "confidence": 50 if mapping.get(fid) else 30,
                    "notes": "",
                }
            )
        letter = None
        if analysis.get("requires_letter_of_intent"):
            letter = (
                f"[Borrador básico — revisar]\n\n"
                f"Estimados miembros del comité,\n\n"
                f"Soy {name or '[TU NOMBRE]'}, de nacionalidad "
                f"{profile.get('nationality', '[TU PAÍS]')}, y postulo a esta beca para "
                f"continuar mis estudios en {profile.get('field_of_study', '')} "
                f"({profile.get('academic_level', '')}).\n\n"
                f"{analysis.get('scholarship_purpose', '')}\n\n"
                f"Atentamente,\n{name or '[TU NOMBRE]'}"
            )
        return {
            "filled_fields": filled,
            "letter_of_intent": letter,
            "submission_checklist": [
                "Revisar cada campo en el portal oficial",
                "Adjuntar documentos solicitados",
                "Enviar antes del deadline",
            ],
            "warnings": [f"Relleno LLM limitado: {error}"],
        }
