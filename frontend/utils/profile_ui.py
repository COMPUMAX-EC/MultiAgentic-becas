"""profile_ui.py — Academic profile form for authenticated users."""
from __future__ import annotations

from database.repository import get_user_profile, save_user_profile


def profile_is_complete(profile: dict) -> bool:
    """Minimum fields required before a quota-backed search."""
    required = ("nationality", "academic_level", "field_of_study", "target_countries")
    return all(str(profile.get(key, "")).strip() for key in required)


def build_search_query(profile: dict, extra_query: str = "") -> str:
    """Combine saved profile with optional free-text preferences."""
    interests = profile.get("interests", "")
    if isinstance(interests, list):
        interests = ", ".join(str(x) for x in interests)
    targets = profile.get("target_countries", "")
    if isinstance(targets, list):
        targets = ", ".join(str(x) for x in targets)
    languages = profile.get("languages", "")
    if isinstance(languages, list):
        languages = ", ".join(str(x) for x in languages)

    lines = [
        f"Nationality: {profile.get('nationality', '').strip()}",
        f"Country of residence: {profile.get('country_of_residence', '').strip()}",
        f"Academic level: {profile.get('academic_level', '').strip()}",
        f"Field of study: {profile.get('field_of_study', '').strip()}",
        f"Target countries: {targets.strip()}",
        f"Languages: {languages.strip()}",
        f"Scholarship type sought: {profile.get('scholarship_type', '').strip()}",
    ]
    if interests:
        lines.append(f"Interests: {interests.strip()}")
    if extra_query.strip():
        lines.append(f"Additional preferences: {extra_query.strip()}")
    return "\n".join(line for line in lines if not line.endswith(": "))


def render_profile_editor(google_sub: str) -> dict:
    """Render profile fields and return the current profile dict. Requires auth."""
    import streamlit as st

    stored = get_user_profile(google_sub)
    session_key = f"_profile_draft_{google_sub}"

    if session_key not in st.session_state and stored:
        st.session_state[session_key] = stored

    def _val(field: str, default: str = "") -> str:
        draft = st.session_state.get(session_key, stored)
        raw = draft.get(field, default) if isinstance(draft, dict) else default
        if isinstance(raw, list):
            return ", ".join(str(x) for x in raw)
        return str(raw or "")

    with st.expander("📋 Tu perfil académico", expanded=not profile_is_complete(stored)):
        st.caption(
            "Las búsquedas usan este perfil. Complétalo antes de buscar "
            "(máx. 5 búsquedas por día)."
        )
        c1, c2 = st.columns(2)
        with c1:
            nationality = st.text_input(
                "Nacionalidad *",
                value=_val("nationality"),
                key=f"prof_nat_{google_sub}",
            )
            residence = st.text_input(
                "País de residencia",
                value=_val("country_of_residence"),
                key=f"prof_res_{google_sub}",
            )
            level = st.selectbox(
                "Nivel académico *",
                ["", "high school", "bachelors", "masters", "phd", "postdoc"],
                index=_level_index(_val("academic_level")),
                key=f"prof_lvl_{google_sub}",
            )
        with c2:
            field = st.text_input(
                "Área de estudio *",
                value=_val("field_of_study"),
                key=f"prof_field_{google_sub}",
            )
            targets = st.text_input(
                "Países objetivo * (separados por coma)",
                value=_val("target_countries"),
                key=f"prof_tgt_{google_sub}",
            )
            scholarship_type = st.text_input(
                "Tipo de beca (ej. full funding, partial)",
                value=_val("scholarship_type"),
                key=f"prof_type_{google_sub}",
            )

        interests = st.text_input(
            "Intereses (separados por coma)",
            value=_val("interests"),
            key=f"prof_int_{google_sub}",
        )
        languages = st.text_input(
            "Idiomas (separados por coma)",
            value=_val("languages"),
            key=f"prof_lang_{google_sub}",
        )

        profile = {
            "nationality": nationality.strip(),
            "country_of_residence": residence.strip(),
            "academic_level": level.strip(),
            "field_of_study": field.strip(),
            "target_countries": targets.strip(),
            "interests": interests.strip(),
            "languages": languages.strip(),
            "scholarship_type": scholarship_type.strip(),
        }

        if st.button("💾 Guardar perfil", type="secondary", key=f"prof_save_{google_sub}"):
            save_user_profile(google_sub, profile)
            st.session_state[session_key] = profile
            st.success("Perfil guardado.")
            st.rerun()

        st.session_state[session_key] = profile

    return st.session_state.get(session_key, profile)


def _level_index(level: str) -> int:
    options = ["", "high school", "bachelors", "masters", "phd", "postdoc"]
    normalized = level.strip().lower()
    for i, opt in enumerate(options):
        if opt and opt in normalized:
            return i
    return 0
