"""
MultiAgentic-Becas — Schemas Pydantic
Define las estructuras de datos del sistema.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────

class AcademicLevel(str, Enum):
    UNDERGRADUATE = "undergraduate"
    MASTER = "master"
    PHD = "phd"
    POSTDOC = "postdoc"
    OTHER = "other"


class LanguageProficiency(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    NATIVE = "native"


class FundingType(str, Enum):
    FULL = "full"           # Cubre todo (matrícula + manutención)
    PARTIAL = "partial"     # Cubre sólo matrícula
    TUITION_ONLY = "tuition_only"
    STIPEND_ONLY = "stipend_only"


class CompatibilityLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# ──────────────────────────────────────────────────────────
# Perfil del usuario
# ──────────────────────────────────────────────────────────

class LanguageSkill(BaseModel):
    language: str
    proficiency: LanguageProficiency


class UserProfile(BaseModel):
    """Perfil estructurado del estudiante."""
    name: Optional[str] = None
    academic_level: AcademicLevel
    field_of_study: str = Field(description="Área de estudio principal")
    specialization: Optional[str] = Field(default=None, description="Especialización dentro del campo")
    country_of_origin: str = Field(description="País de origen/residencia")
    target_countries: list[str] = Field(
        default_factory=list,
        description="Países donde quiere estudiar. Vacío = cualquier país"
    )
    gpa: Optional[float] = Field(
        default=None,
        ge=0.0, le=10.0,
        description="Promedio académico en escala 0-10"
    )
    languages: list[LanguageSkill] = Field(default_factory=list)
    financial_need: bool = Field(default=False)
    special_characteristics: list[str] = Field(
        default_factory=list,
        description="Ej: indígena, primera generación, discapacidad"
    )
    career_goals: Optional[str] = Field(
        default=None,
        description="Objetivos profesionales (breve descripción)"
    )
    publications: int = Field(default=0, description="Número de publicaciones académicas")
    work_experience_years: int = Field(default=0)


# ──────────────────────────────────────────────────────────
# Beca
# ──────────────────────────────────────────────────────────

class Scholarship(BaseModel):
    """Información de una beca encontrada."""
    name: str
    provider: str = Field(description="Organización que otorga la beca")
    url: str
    description: str
    funding_type: FundingType = FundingType.FULL
    amount_usd: Optional[float] = Field(default=None, description="Monto en USD si aplica")
    deadline: Optional[str] = Field(default=None, description="Fecha límite en formato YYYY-MM-DD o descripción")
    target_countries: list[str] = Field(
        default_factory=list,
        description="Países de origen elegibles. Vacío = todos"
    )
    host_countries: list[str] = Field(
        default_factory=list,
        description="Países donde se estudia"
    )
    eligible_levels: list[AcademicLevel] = Field(default_factory=list)
    fields_of_study: list[str] = Field(
        default_factory=list,
        description="Áreas de estudio elegibles. Vacío = todas"
    )
    requirements: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    language_requirements: list[LanguageSkill] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────
# Evaluación
# ──────────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    academic_match: int = Field(ge=0, le=25)
    eligibility_match: int = Field(ge=0, le=25)
    goals_alignment: int = Field(ge=0, le=25)
    competitiveness: int = Field(ge=0, le=25)


class ScholarshipEvaluation(BaseModel):
    scholarship: Scholarship
    score: int = Field(ge=0, le=100)
    breakdown: ScoreBreakdown
    recommendation: CompatibilityLevel
    key_strengths: list[str]
    key_gaps: list[str]
    notes: str


# ──────────────────────────────────────────────────────────
# Reporte final
# ──────────────────────────────────────────────────────────

class BecasReport(BaseModel):
    """Reporte final generado por el WriterAgent."""
    user_profile: UserProfile
    evaluations: list[ScholarshipEvaluation]
    summary: str = Field(description="Resumen ejecutivo del reporte")
    top_recommendations: list[str] = Field(description="Top 3 becas recomendadas con justificación")
    next_steps: list[str] = Field(description="Acciones concretas a tomar")
    motivation_letter_draft: Optional[str] = Field(
        default=None,
        description="Borrador de carta de motivación para la beca #1"
    )
