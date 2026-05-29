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

    academic_lvl = profile.get("academic_level", "").strip().lower()
    bachelors_stage = profile.get("bachelors_stage", "").strip().lower()
    
    display_academic_level = profile.get("academic_level", "").strip()
    scholarship_type_sought = profile.get("scholarship_type", "").strip()
    
    seeking_info = ""
    if academic_lvl == "bachelors":
        if bachelors_stage == "beginning":
            display_academic_level = "Bachelors (Beginning / Mid-way)"
            scholarship_type_sought = "internship (Pasantías)"
            seeking_info = "Looking for: Internships (Pasantías) to gain professional experience during undergraduate studies"
        elif bachelors_stage == "finishing":
            display_academic_level = "Bachelors (Finishing / Graduating)"
            scholarship_type_sought = "scholarship (Maestrías / Master's degree)"
            seeking_info = "Looking for: Master's degrees / Maestrías to study right after graduating"

    lines = [
        f"Nationality: {profile.get('nationality', '').strip()}",
        f"Country of residence: {profile.get('country_of_residence', '').strip()}",
        f"Academic level: {display_academic_level}",
        f"Field of study: {profile.get('field_of_study', '').strip()}",
        f"Target countries: {targets.strip()}",
        f"Languages: {languages.strip()}",
        f"Scholarship type sought: {scholarship_type_sought}",
    ]
    if seeking_info:
        lines.append(seeking_info)
    if interests:
        lines.append(f"Interests: {interests.strip()}")
    if extra_query.strip():
        lines.append(f"Additional preferences: {extra_query.strip()}")
    return "\n".join(line for line in lines if not line.endswith(": "))


def render_profile_editor(google_sub: str) -> dict:
    """Render profile fields as a premium step-by-step wizard or a clean dashboard summary."""
    import streamlit as st

    stored = get_user_profile(google_sub)
    session_key = f"_profile_draft_{google_sub}"
    step_key = f"_profile_step_{google_sub}"
    edit_key = f"_editing_profile_{google_sub}"

    if session_key not in st.session_state:
        initial_draft = stored if isinstance(stored, dict) else {}
        if "target_countries" not in initial_draft or not initial_draft.get("target_countries"):
            initial_draft["target_countries"] = "Global"
        st.session_state[session_key] = initial_draft

    if step_key not in st.session_state:
        st.session_state[step_key] = 1

    draft = st.session_state[session_key]
    current_step = st.session_state[step_key]

    # Initialize profile early to prevent UnboundLocalError
    profile = {
        "nationality": draft.get("nationality", "").strip(),
        "country_of_residence": draft.get("country_of_residence", "").strip(),
        "academic_level": draft.get("academic_level", "").strip(),
        "field_of_study": draft.get("field_of_study", "").strip(),
        "target_countries": draft.get("target_countries", "Global").strip(),
        "interests": draft.get("interests", "").strip(),
        "languages": draft.get("languages", "").strip(),
        "scholarship_type": draft.get("scholarship_type", "scholarship") or "scholarship",
        "bachelors_stage": draft.get("bachelors_stage", "")
    }

    with st.expander("📋 Tu perfil académico", expanded=not profile_is_complete(stored)):
        # Show Dashboard Summary if profile is complete and not explicitly editing
        if profile_is_complete(stored) and not st.session_state.get(edit_key, False):
            level_mapping = {
                "high school": "Bachillerato 🎒",
                "bachelors": "Pregrado 🎓",
                "masters": "Maestría 📜",
                "phd": "Doctorado 🔬"
            }
            raw_lvl = stored.get("academic_level", "").lower().strip()
            display_lvl = level_mapping.get(raw_lvl, stored.get("academic_level", "").title())
            
            # Format display label according to stage if it's bachelors
            if raw_lvl == "bachelors":
                stage = stored.get("bachelors_stage") or draft.get("bachelors_stage", "")
                if stage == "beginning":
                    display_lvl += " (Comenzando - Busca Pasantías)"
                elif stage == "finishing":
                    display_lvl += " (Terminando - Busca Maestrías)"

            st.markdown(f"""
            <h3 style="color:#ffffff;font-size:1.25rem;font-weight:600;margin-top:0.4rem;margin-bottom:0.2rem;">🎓 Tu Perfil Académico Completo</h3>
            <p style="color:#64748b;font-size:0.8rem;margin-bottom:1rem;">Este perfil es el que utiliza la IA de DevIALabs para sugerirte y aplicar automáticamente a becas.</p>
            
            <div style="background:rgba(26,26,26,0.6);border:1px solid rgba(157,255,0,0.2);border-radius:14px;padding:1.2rem;margin-bottom:1rem;backdrop-filter:blur(8px);">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;font-size:0.88rem;color:#cbd5e1;">
                    <div>🌍 <strong>Nacionalidad:</strong> {stored.get('nationality', '—')}</div>
                    <div>🏠 <strong>País de residencia:</strong> {stored.get('country_of_residence', '—')}</div>
                    <div>🎓 <strong>Nivel académico:</strong> {display_lvl}</div>
                    <div>📚 <strong>Área de estudio:</strong> {stored.get('field_of_study', '—')}</div>
                    <div>🎯 <strong>Destino objetivo:</strong> {stored.get('target_countries', '—')}</div>
                    <div>🗣️ <strong>Idiomas:</strong> {stored.get('languages', '—')}</div>
                </div>
                <div style="margin-top:0.8rem;border-top:1px solid rgba(255,255,255,0.08);padding-top:0.6rem;color:#cbd5e1;font-size:0.88rem;">
                    ✨ <strong>Intereses académicos:</strong><br>
                    <span style="color:#9DFF00;font-size:0.82rem;font-style:italic;">{stored.get('interests', 'Sin intereses registrados.')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("✏️ Modificar mi Perfil (Paso a Paso)", use_container_width=True, key=f"btn_edit_profile_{google_sub}"):
                st.session_state[edit_key] = True
                st.session_state[step_key] = 1
                st.rerun()

            return stored

        # --- STEP-BY-STEP WIZARD ---
        progress_pct = int((current_step - 1) / 6 * 100)
        st.progress(progress_pct / 100)
        step_names = {
            1: "Nacionalidad 🌍",
            2: "País de residencia 🏠",
            3: "Nivel académico 🎓",
            4: "Área de estudio 📚",
            5: "País objetivo 🎯",
            6: "Intereses académicos ✨",
            7: "Idiomas 🗣️"
        }
        st.markdown(f"<div style='font-size:0.75rem;color:#9DFF00;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.8rem;'>Paso {current_step} de 7: {step_names[current_step]}</div>", unsafe_allow_html=True)

        # STEP 1: Nacionalidad 🌍
        if current_step == 1:
            st.markdown("<h4 style='color:#e2e8f0;font-size:1.15rem;margin-bottom:0.2rem;'>🌍 ¿Cuál es tu nacionalidad? *</h4>", unsafe_allow_html=True)
            st.caption("Selecciona tu país de origen para filtrar becas elegibles.")

            nat_options = {
                "Ecuador 🇪🇨": "Ecuador",
                "Colombia 🇨🇴": "Colombia",
                "Perú 🇵🇪": "Peru",
                "Venezuela 🇻🇪": "Venezuela",
                "Argentina 🇦🇷": "Argentina",
                "Chile 🇨🇱": "Chile",
            }

            cols = st.columns(3)
            current_nat = draft.get("nationality", "")
            for idx, (display_name, val_name) in enumerate(nat_options.items()):
                col_idx = idx % 3
                btn_type = "primary" if current_nat.lower() == val_name.lower() else "secondary"
                if cols[col_idx].button(
                    display_name,
                    key=f"btn_nat_{val_name}_{google_sub}",
                    use_container_width=True,
                    type=btn_type
                ):
                    draft["nationality"] = val_name
                    draft["country_of_residence"] = val_name
                    st.session_state[session_key] = draft
                    st.session_state[step_key] = 2
                    st.rerun()

            st.write("")
            other_country = st.text_input(
                "O escribe tu nacionalidad si no está arriba:",
                value=draft.get("nationality", "") if draft.get("nationality", "") not in nat_options.values() else "",
                placeholder="Ej: España, México, Estados Unidos...",
                key=f"prof_nat_manual_{google_sub}"
            )
            if other_country:
                draft["nationality"] = other_country.strip()
                st.session_state[session_key] = draft

            st.markdown("<br>", unsafe_allow_html=True)
            if draft.get("nationality"):
                if st.button("Siguiente ➔", type="primary", use_container_width=True, key=f"next_1_{google_sub}"):
                    st.session_state[step_key] = 2
                    st.rerun()

        # STEP 2: País de residencia 🏠
        elif current_step == 2:
            st.markdown("<h4 style='color:#e2e8f0;font-size:1.15rem;margin-bottom:0.2rem;'>🏠 ¿En qué país resides actualmente? *</h4>", unsafe_allow_html=True)
            st.caption("Tu lugar físico de residencia actual.")

            nat = draft.get("nationality", "Ecuador")

            # Quick button: same as nationality
            if st.button(f"📍 Igual que mi nacionalidad ({nat})", use_container_width=True, key=f"btn_res_same_{google_sub}"):
                draft["country_of_residence"] = nat
                st.session_state[session_key] = draft
                st.session_state[step_key] = 3
                st.rerun()

            residence = st.text_input(
                "Escribe tu país de residencia actual:",
                value=draft.get("country_of_residence", nat),
                placeholder="Ej: Ecuador, Colombia, España...",
                key=f"prof_res_{google_sub}",
            )
            draft["country_of_residence"] = residence.strip()
            st.session_state[session_key] = draft

            st.markdown("<br>", unsafe_allow_html=True)
            nav_cols = st.columns(2)
            if nav_cols[0].button("⬅️ Anterior", use_container_width=True, key=f"back_2_{google_sub}"):
                st.session_state[step_key] = 1
                st.rerun()
            if draft.get("country_of_residence"):
                if nav_cols[1].button("Siguiente ➔", type="primary", use_container_width=True, key=f"next_2_{google_sub}"):
                    st.session_state[step_key] = 3
                    st.rerun()

        # STEP 3: Nivel académico 🎓
        elif current_step == 3:
            st.markdown("<h4 style='color:#e2e8f0;font-size:1.15rem;margin-bottom:0.2rem;'>🎓 ¿Cuál es tu nivel académico actual? *</h4>", unsafe_allow_html=True)
            st.caption("Filtra las becas según el grado al que estás postulando o tu nivel de estudios actual.")

            levels = {
                "high school": "Bachillerato 🎒",
                "bachelors": "Pregrado 🎓",
                "masters": "Maestría 📜",
                "phd": "Doctorado 🔬"
            }

            cols = st.columns(4)
            current_lvl = draft.get("academic_level", "").lower().strip()
            for idx, (level_key_val, display_name) in enumerate(levels.items()):
                btn_type = "primary" if current_lvl == level_key_val else "secondary"
                if cols[idx].button(
                    display_name,
                    key=f"btn_lvl_{level_key_val}_{google_sub}",
                    use_container_width=True,
                    type=btn_type
                ):
                    draft["academic_level"] = level_key_val
                    # If not bachelors, clear stage and go to step 4
                    if level_key_val != "bachelors":
                        draft["bachelors_stage"] = ""
                        draft["scholarship_type"] = "scholarship"
                        st.session_state[session_key] = draft
                        st.session_state[step_key] = 4
                        st.rerun()
                    else:
                        st.session_state[session_key] = draft
                        st.rerun()

            # Render sub-question if they selected "bachelors" (Pregrado)
            if current_lvl == "bachelors":
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<h5 style='color:#9DFF00;font-size:1rem;margin-bottom:0.2rem;'>📍 ¿En qué etapa de tu carrera de Pregrado te encuentras? *</h5>", unsafe_allow_html=True)
                st.caption("Esto nos ayuda a recomendarte Pasantías (si estás comenzando) o Maestrías (si estás terminando).")
                
                stage_cols = st.columns(2)
                current_stage = draft.get("bachelors_stage", "")
                
                # Option 1: Comenzando / Mitad (Pasantías)
                btn_type_beg = "primary" if current_stage == "beginning" else "secondary"
                if stage_cols[0].button(
                    "Comenzando / Mitad (Buscar Pasantías) 💼",
                    key=f"btn_stage_beg_{google_sub}",
                    use_container_width=True,
                    type=btn_type_beg
                ):
                    draft["bachelors_stage"] = "beginning"
                    draft["scholarship_type"] = "internship"
                    st.session_state[session_key] = draft
                    st.session_state[step_key] = 4
                    st.rerun()
                    
                # Option 2: Terminando / Último año (Maestrías)
                btn_type_fin = "primary" if current_stage == "finishing" else "secondary"
                if stage_cols[1].button(
                    "Terminando / Último año (Buscar Maestrías) 🎓",
                    key=f"btn_stage_fin_{google_sub}",
                    use_container_width=True,
                    type=btn_type_fin
                ):
                    draft["bachelors_stage"] = "finishing"
                    draft["scholarship_type"] = "scholarship"
                    st.session_state[session_key] = draft
                    st.session_state[step_key] = 4
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            nav_cols = st.columns(2)
            if nav_cols[0].button("⬅️ Anterior", use_container_width=True, key=f"back_3_{google_sub}"):
                st.session_state[step_key] = 2
                st.rerun()
            
            can_proceed = draft.get("academic_level") and (draft.get("academic_level") != "bachelors" or draft.get("bachelors_stage"))
            if can_proceed:
                if nav_cols[1].button("Siguiente ➔", type="primary", use_container_width=True, key=f"next_3_{google_sub}"):
                    st.session_state[step_key] = 4
                    st.rerun()

        # STEP 4: Área de estudio 📚
        elif current_step == 4:
            st.markdown("<h4 style='color:#e2e8f0;font-size:1.15rem;margin-bottom:0.2rem;'>📚 ¿Cuál es tu área de estudio o carrera? *</h4>", unsafe_allow_html=True)
            st.caption("Escribe tu carrera principal o especialidad académica.")

            suggestions = [
                "Ingeniería de Sistemas",
                "Medicina / Salud",
                "Administración / Finanzas",
                "Ciencias Políticas / Derecho",
                "Psicología / Educación",
                "Artes / Humanidades"
            ]

            st.markdown("<div style='margin-bottom:0.4rem;color:#94a3b8;font-size:0.85rem;font-weight:500;'>Selección rápida:</div>", unsafe_allow_html=True)
            sug_cols = st.columns(3)
            for idx, sug in enumerate(suggestions):
                col_idx = idx % 3
                if sug_cols[col_idx].button(sug, key=f"sug_{idx}_{google_sub}", use_container_width=True):
                    draft["field_of_study"] = sug
                    st.session_state[session_key] = draft
                    st.session_state[step_key] = 5
                    st.rerun()

            st.write("")
            field = st.text_input(
                "O escribe tu área de estudio personalizada:",
                value=draft.get("field_of_study", ""),
                placeholder="Ej: Ingeniería Mecánica, Inteligencia Artificial, Marketing...",
                key=f"prof_field_{google_sub}",
            )
            draft["field_of_study"] = field.strip()
            st.session_state[session_key] = draft

            st.markdown("<br>", unsafe_allow_html=True)
            nav_cols = st.columns(2)
            if nav_cols[0].button("⬅️ Anterior", use_container_width=True, key=f"back_4_{google_sub}"):
                st.session_state[step_key] = 3
                st.rerun()
            if draft.get("field_of_study"):
                if nav_cols[1].button("Siguiente ➔", type="primary", use_container_width=True, key=f"next_4_{google_sub}"):
                    st.session_state[step_key] = 5
                    st.rerun()

        # STEP 5: País objetivo 🎯
        elif current_step == 5:
            st.markdown("<h4 style='color:#e2e8f0;font-size:1.15rem;margin-bottom:0.2rem;'>🎯 ¿Cuál es tu destino de estudios objetivo? *</h4>", unsafe_allow_html=True)
            st.caption("Determina la cobertura geográfica de las becas recomendadas.")

            tgt_options = {
                "Todo el mundo 🌍": "Global",
                "Latinoamérica 🌎": "Latinoamerica",
                "Europa 🇪🇺": "Europa",
            }

            cols = st.columns(3)
            current_tgt = draft.get("target_countries", "Global")
            for idx, (display_name, val_name) in enumerate(tgt_options.items()):
                btn_type = "primary" if current_tgt == val_name else "secondary"
                if cols[idx].button(
                    display_name,
                    key=f"btn_tgt_{val_name}_{google_sub}",
                    use_container_width=True,
                    type=btn_type
                ):
                    draft["target_countries"] = val_name
                    st.session_state[session_key] = draft
                    st.session_state[step_key] = 6
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            nav_cols = st.columns(2)
            if nav_cols[0].button("⬅️ Anterior", use_container_width=True, key=f"back_5_{google_sub}"):
                st.session_state[step_key] = 4
                st.rerun()
            if draft.get("target_countries"):
                if nav_cols[1].button("Siguiente ➔", type="primary", use_container_width=True, key=f"next_5_{google_sub}"):
                    st.session_state[step_key] = 6
                    st.rerun()

        # STEP 6: Intereses académicos ✨
        elif current_step == 6:
            st.markdown("<h4 style='color:#e2e8f0;font-size:1.15rem;margin-bottom:0.2rem;'>✨ Agrega temas o intereses académicos</h4>", unsafe_allow_html=True)
            st.caption("Pulsar Enter agregará el interés a tu pila para afinar las recomendaciones de la IA.")

            raw_ints = draft.get("interests", "")
            if isinstance(raw_ints, list):
                interests_list = [str(x).strip() for x in raw_ints if str(x).strip()]
            else:
                interests_list = [x.strip() for x in str(raw_ints or "").split(",") if x.strip()]

            if interests_list:
                st.markdown("<div style='margin-bottom:0.4rem;color:#94a3b8;font-size:0.85rem;font-weight:500;'>Tus intereses actuales (haz clic para eliminar):</div>", unsafe_allow_html=True)
                for idx in range(0, len(interests_list), 4):
                    row_ints = interests_list[idx:idx + 4]
                    cols = st.columns(4)
                    for col_idx, interest in enumerate(row_ints):
                        if cols[col_idx].button(
                            f"❌ {interest}",
                            key=f"del_int_{interest}_{google_sub}_{idx}_{col_idx}",
                            use_container_width=True
                        ):
                            interests_list.remove(interest)
                            draft["interests"] = ", ".join(interests_list)
                            st.session_state[session_key] = draft
                            st.rerun()

            new_interest = st.text_input(
                "Escribe un interés y presiona Enter:",
                placeholder="Ej: Inteligencia Artificial, Ciberseguridad, Finanzas...",
                value="",
                key=f"new_interest_input_{google_sub}"
            )
            if new_interest:
                cleaned = new_interest.strip()
                if cleaned and cleaned not in interests_list:
                    interests_list.append(cleaned)
                    draft["interests"] = ", ".join(interests_list)
                    st.session_state[session_key] = draft
                    del st.session_state[f"new_interest_input_{google_sub}"]
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            nav_cols = st.columns(2)
            if nav_cols[0].button("⬅️ Anterior", use_container_width=True, key=f"back_6_{google_sub}"):
                st.session_state[step_key] = 5
                st.rerun()
            if nav_cols[1].button("Siguiente ➔", type="primary", use_container_width=True, key=f"next_6_{google_sub}"):
                st.session_state[step_key] = 7
                st.rerun()

        # STEP 7: Idiomas 🗣️
        elif current_step == 7:
            st.markdown("<h4 style='color:#e2e8f0;font-size:1.15rem;margin-bottom:0.2rem;'>🗣️ ¿Qué idiomas dominas?</h4>", unsafe_allow_html=True)
            st.caption("Español e Inglés están seleccionados por defecto.")

            raw_langs = draft.get("languages", "")
            if isinstance(raw_langs, list):
                current_langs = [str(x).strip() for x in raw_langs if str(x).strip()]
            else:
                current_langs = [x.strip() for x in str(raw_langs or "").split(",") if x.strip()]

            if not current_langs:
                current_langs = ["Español", "Inglés"]

            available_options = ["Español", "Inglés", "Alemán", "Francés", "Portugués", "Italiano", "Chino", "Japonés"]
            for lang in current_langs:
                if lang not in available_options:
                    available_options.append(lang)

            selected_langs = st.multiselect(
                "Idiomas dominados:",
                options=available_options,
                default=current_langs,
                key=f"prof_lang_multi_{google_sub}"
            )

            languages = ", ".join(selected_langs)

            profile["languages"] = languages.strip()

            st.markdown("<br>", unsafe_allow_html=True)
            nav_cols = st.columns(2)
            if nav_cols[0].button("⬅️ Anterior", use_container_width=True, key=f"back_7_{google_sub}"):
                st.session_state[step_key] = 6
                st.rerun()

            if nav_cols[1].button("💾 Guardar y Finalizar", type="primary", use_container_width=True, key=f"save_profile_{google_sub}"):
                save_user_profile(google_sub, profile)
                st.session_state[session_key] = profile
                st.session_state[step_key] = 1  # Reset to step 1
                st.session_state[edit_key] = False  # Exit editing mode
                st.success("🎉 ¡Tu perfil académico ha sido guardado con éxito!")
                st.rerun()

    return profile


def _level_index(level: str) -> int:
    options = ["", "high school", "bachelors", "masters", "phd"]
    normalized = level.strip().lower()
    for i, opt in enumerate(options):
        if opt and opt in normalized:
            return i
    return 0
