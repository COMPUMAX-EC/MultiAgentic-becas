# 🎓 MultiAgentic-Becas

> **AMD Developer Hackathon 2026 — Track 1: AI Agents & Agentic Workflows**  
> Sistema multi-agente para búsqueda inteligente de becas académicas, orquestado con LangGraph y ejecutado sobre AMD Instinct MI300X.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange)](https://langchain-ai.github.io/langgraph/)
[![AMD](https://img.shields.io/badge/AMD-MI300X%20%7C%20ROCm-red)](https://cloud.amd.com)
[![uv](https://img.shields.io/badge/uv-package%20manager-purple)](https://github.com/astral-sh/uv)

---

## 📋 Tabla de Contenidos

- [¿Qué hace este proyecto?](#-qué-hace-este-proyecto)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Configuración del Entorno](#-configuración-del-entorno)
- [Levantar el Servicio — Modo Local (Ollama)](#-levantar-el-servicio--modo-local-ollama)
- [Levantar el Servicio — AMD Developer Cloud](#-levantar-el-servicio--amd-developer-cloud)
- [Comandos del Pipeline CLI](#-comandos-del-pipeline-cli)
- [Roadmap — 15 Fases](#-roadmap--15-fases)

---

## 🤖 ¿Qué hace este proyecto?

MultiAgentic-Becas toma un perfil de estudiante en JSON y ejecuta un pipeline de agentes especializados que:

1. **Normaliza** el perfil del estudiante (10 dimensiones)
2. **Genera** queries de búsqueda inteligentes
3. **Busca** becas en tiempo real en la web (DuckDuckGo)
4. **Valida** y filtra fuentes por confiabilidad
5. **Extrae** datos estructurados de páginas de becas
6. **Compara** cada beca contra el perfil (matching)
7. **Rankea** las mejores opciones y las persiste en SQLite
8. **Expone** la Knowledge Base vía UI Streamlit con búsqueda semántica

```
data/profiles/sample_profile.json
        ↓
uv run python main.py --rank-scholarships
        ↓
[ ProfileAgent → QueryAgent → SearchAgent → SourceValidator
  → PageReader → ExtractionAgent → MatchingAgent → RankingAgent ]
        ↓
data/results/ranking_result_<timestamp>.json  +  SQLite KB
        ↓
uv run streamlit run frontend/app.py
        ↓
UI con búsqueda semántica + login Google + cuota 5/día
```

---

## 🏗️ Arquitectura del Sistema

### Pipeline CLI (main.py — 12 fases)

```
ProfileAgent → QueryAgent → SearchAgent → SourceValidatorAgent
    → PageReaderAgent → ExtractionAgent → MatchingAgent → RankingAgent
```

Cada fase se activa con un flag CLI (`--rank-scholarships` ejecuta todo el pipeline completo).

### Motor LLM — Triple Backend

| `LLM_PROVIDER` | Cuándo usarlo | Hardware |
|----------------|--------------|----------|
| `ollama` | Desarrollo local sin GPU | CPU local |
| `vllm` | Producción / Hackathon con MI300X | AMD MI300X (192 GB VRAM) |
| `gcp_cpu` | Alternativa cloud sin GPU | GCP VM CPU |

El switch se hace **solo con una variable de entorno** — sin cambiar código.

---

## ⚙️ Configuración del Entorno

### 1. Clonar y crear el entorno

```bash
git clone https://github.com/COMPUMAX-EC/MultiAgentic-becas.git
cd MultiAgentic-becas

# Instalar uv si no lo tienes
pip install uv

# Crear entorno virtual e instalar dependencias
uv sync
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con las variables correctas según tu backend:

```env
# ── Backend activo — cambia SOLO esta variable para switchar ──────────────────
# Opciones: ollama | vllm | gcp_cpu
LLM_PROVIDER=ollama

# ── Ollama (desarrollo local, sin GPU) ────────────────────────────────────────
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# ── AMD MI300X via vLLM (producción / hackathon) ──────────────────────────────
REMOTE_LLM_BASE_URL=http://<TU_IP_DROPLET>:8000/v1
REMOTE_LLM_API_KEY=not-required
REMOTE_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
REMOTE_LLM_ENDPOINT_TYPE=openai_compatible

# ── GCP VM con CPU (alternativa sin GPU) ──────────────────────────────────────
GCP_VM_BASE_URL=http://<TU_IP_GCP>:11434/v1
GCP_VM_MODEL=qwen2.5:3b

# ── Google OAuth 2.0 (login + cuota 5 búsquedas/día) ─────────────────────────
GOOGLE_CLIENT_ID=<tu-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<tu-client-secret>
GOOGLE_REDIRECT_URI=http://localhost:8501/
SESSION_SECRET_KEY=<genera con: python -c "import secrets; print(secrets.token_hex(32))">
MAX_QUERIES_PER_USER=5
```

> ⚠️ **Variables críticas**: usa `LLM_PROVIDER` (no `LLM_BACKEND`), `OLLAMA_HOST` (no `OLLAMA_BASE_URL`), `REMOTE_LLM_BASE_URL` (no `VLLM_BASE_URL`).

### 3. Configurar Google OAuth (para la UI)

1. Ir a [console.cloud.google.com](https://console.cloud.google.com/)
2. **APIs & Services → Credentials → Create OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Authorized redirect URIs: `http://localhost:8501/` (desarrollo) o tu dominio (producción)
5. Copiar `Client ID` y `Client Secret` al `.env`

---

## 🟡 Levantar el Servicio — Modo Local (Ollama)

> Sin GPU. Para desarrollo y pruebas.

### Paso 1 — Instalar y levantar Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Descargar el modelo
ollama pull qwen2.5:7b-instruct
```

### Paso 2 — Ejecutar el pipeline CLI (llena la Knowledge Base)

```bash
uv run python main.py --rank-scholarships
```

El pipeline tarda ~5–15 minutos según la conexión. Guarda resultados en `data/results/` y en SQLite.

### Paso 3 — Levantar la UI Streamlit

```bash
uv run streamlit run frontend/app.py
```

Abre **http://localhost:8501** → inicia sesión con Google → busca becas.

### Probar la conexión LLM

```bash
uv run python main.py --test-llm
```

---

## 🔴 Levantar el Servicio — AMD Developer Cloud

> Con GPU AMD Instinct MI300X.

### Paso 1 — Crear el GPU Droplet

1. Ir a **https://cloud.amd.com**
2. **Create GPU Droplet**
3. Seleccionar:
   - **Plan:** `MI300X` — 1 GPU, 192 GB VRAM, $1.99/hr ⚠️ *(NO el x8, que cuesta $15.92/hr)*
   - **Image:** `vLLM Quick Start` — vLLM 0.17.1, ROCm 7.2.0
4. Agregar tu SSH key
5. **Create** → anotar la IP pública

> 💡 Con $100 de créditos tienes ~50 horas de cómputo con el plan de 1 GPU.

### Paso 2 — Conectarse y lanzar el modelo

```bash
ssh root@<TU_IP>

vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len 8192 \
  --dtype auto

ufw allow 8000
```

Cuando veas `INFO: Application startup complete.` el endpoint está listo.

### Paso 3 — Verificar conexión

```bash
curl http://<TU_IP>:8000/v1/models
```

### Paso 4 — Configurar `.env` local

```env
LLM_PROVIDER=vllm
REMOTE_LLM_BASE_URL=http://<TU_IP>:8000/v1
REMOTE_LLM_API_KEY=not-required
REMOTE_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
REMOTE_LLM_ENDPOINT_TYPE=openai_compatible
```

### Paso 5 — Ejecutar pipeline y UI

```bash
# Pipeline (llena la Knowledge Base con becas rankeadas)
uv run python main.py --rank-scholarships

# UI
uv run streamlit run frontend/app.py
```

> ⚠️ **Importante:** Cuando termines, **destruye el Droplet** desde el panel. El almacenamiento sigue cobrando si solo se apaga.

---

## 🖥️ Comandos del Pipeline CLI

```bash
# Probar conexión LLM
uv run python main.py --test-llm

# Normalizar perfil (Fase 3)
uv run python main.py

# Generar queries de búsqueda (Fase 4)
uv run python main.py --generate-queries

# Buscar en la web (Fase 5)
uv run python main.py --search-web

# Validar fuentes (Fase 6)
uv run python main.py --validate-sources

# Leer y limpiar páginas (Fase 7)
uv run python main.py --read-pages

# Extraer becas (Fase 8)
uv run python main.py --extract-scholarships

# Guardar en Knowledge Base SQLite (Fase 9)
uv run python main.py --save-knowledge-base

# Recuperar becas conocidas (Fase 10)
uv run python main.py --retrieve-known

# Matching perfil ↔ becas (Fase 11)
uv run python main.py --match-scholarships

# Pipeline completo + ranking (Fase 12) ← el más usado
uv run python main.py --rank-scholarships

# Actualizar becas conocidas (Fase 13)
uv run python main.py --refresh-known

# Demo técnico del hackathon (Fase 15)
uv run python main.py --demo

# Perfil personalizado
uv run python main.py --rank-scholarships --profile data/profiles/mi_perfil.json

# UI Streamlit (separado del CLI)
uv run streamlit run frontend/app.py
```

---

## 🗺️ Roadmap — 15 Fases

| # | Fase | Descripción |
|---|------|-------------|
| 1 | Base Project & Local CLI | Estructura base del proyecto y CLI de entrada |
| 2 | Local Qwen Integration | Conexión con Qwen via Ollama para desarrollo local |
| 3 | Profile Intelligence Layer | Normalización del perfil de usuario (10 dimensiones) |
| 4 | Query Generation Agent | Generación inteligente de queries de búsqueda |
| 5 | Web Search Layer | Búsqueda de páginas en internet (DuckDuckGo + BS4) |
| 6 | Source Intelligence Layer | Validación de calidad de fuentes |
| 7 | Page Reading & Cleaning | Lectura y limpieza de páginas web |
| 8 | Scholarship Extraction Agent | Extracción de becas desde texto |
| 9 | Scholarship Knowledge Base | Almacenamiento de conocimiento reutilizable (SQLite) |
| 10 | RAG & Retrieval Layer | Recuperación de becas ya conocidas |
| 11 | Eligibility & Matching Layer | Comparación perfil vs cada beca |
| 12 | Ranking & Recommendation | Ranking y recomendación final |
| 13 | Refresh & Global Scalability | Actualización periódica + escalabilidad |
| 14 | AMD Cloud / vLLM Compatibility | Migración a AMD MI300X con vLLM |
| 15 | Hackathon Technical Demo | Demo técnico final del Hackathon |

---

## 🧪 Ejecutar Tests

```bash
uv run pytest tests/ -v
```

---

## 📄 Licencia

MIT — AMD Developer Hackathon 2026
