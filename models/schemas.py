"""
MultiAgentic-Becas — Schemas Pydantic
Versión final "Bulletproof" para cualquier tipo de prompt.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field, validator


# --- Enums ---

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
    FULL = "full"
    PARTIAL = "partial"
    TUITION_ONLY = "tuition_only"
    STIPEND_ONLY = "stipend_only"

class CompatibilityLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# --- Estructuras Internas ---

class LanguageSkill(BaseModel):
    language: str = Field(default="English")
    proficiency: LanguageProficiency = Field(default=LanguageProficiency.BASIC)


# --- Perfil del Usuario (Versión Ultra-Resiliente) ---

class UserProfile(BaseModel):
    """
    Perfil diseñado para no fallar nunca. 
    Si el agente no extrae algo, el sistema asume valores base.
    """
    name: Optional[str] = Field(default="Estudiante")
    
    # Si el agente no detecta nivel, asume pregrado por defecto
    academic_level: AcademicLevel = Field(default=AcademicLevel.UNDERGRADUATE)
    
    # Se inicializa como lista vacía para evitar errores de tipo
    field_of_study: List[str] = Field(default_factory=list)
    
    specialization: Optional[str] = Field(default=None)
    
    # CAMBIO CRÍTICO: Valor por defecto 'Ecuador' si el prompt no lo dice
    country_of_origin: str = Field(default="Ecuador")
    
    target_countries: List[str] = Field(default_factory=list)
    
    # Notas: Escala 0-10 (UPEC / Ecuador)
    gpa: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    
    languages: List[LanguageSkill] = Field(default_factory=list)
    financial_need: bool = Field(default=True)
    special_characteristics: List[str] = Field(default_factory=list)
    career_goals: Optional[str] = Field(default=None)
    publications: int = Field(default=0)
    work_experience_years: int = Field(default=0)

    # VALIDADOR DE SEGURIDAD TOTAL: 
    # Corrige fallos comunes del LLM (enviar strings en vez de listas o enviar None)
    @validator('field_of_study', 'target_countries', 'special_characteristics', pre=True)
    def validate_lists(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @validator('country_of_origin', pre=True)
    def validate_country(cls, v):
        if v is None or v == "":
            return "Ecuador"
        return v


# --- Beca y Evaluación ---

class Scholarship(BaseModel):
    name: str
    provider: str
    url: str
    description: str
    funding_type: FundingType = FundingType.FULL
    amount_usd: Optional[float] = None
    deadline: Optional[str] = None
    target_countries: List[str] = Field(default_factory=list)
    host_countries: List[str] = Field(default_factory=list)
    eligible_levels: List[AcademicLevel] = Field(default_factory=list)
    fields_of_study: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    language_requirements: List[LanguageSkill] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    academic_match: int = Field(default=0, ge=0, le=25)
    eligibility_match: int = Field(default=0, ge=0, le=25)
    goals_alignment: int = Field(default=0, ge=0, le=25)
    competitiveness: int = Field(default=0, ge=0, le=25)


class ScholarshipEvaluation(BaseModel):
    scholarship: Scholarship
    score: int = Field(default=0, ge=0, le=100)
    breakdown: ScoreBreakdown          
    recommendation: CompatibilityLevel = Field(default=CompatibilityLevel.MEDIUM)
    key_strengths: List[str] = Field(default_factory=list)
    key_gaps: List[str] = Field(default_factory=list)
    notes: str = ""


class BecasReport(BaseModel):
    user_profile: UserProfile
    evaluations: List[ScholarshipEvaluation] = Field(default_factory=list)
    summary: str = Field(default="No se pudo generar un resumen detallado.")
    top_recommendations: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    motivation_letter_draft: Optional[str] = None
