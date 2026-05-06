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
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Configuración del Entorno](#-configuración-del-entorno)
- [Levantar el Servicio — Modo Local (Ollama)](#-levantar-el-servicio--modo-local-ollama)
- [Levantar el Servicio — AMD Developer Cloud](#-levantar-el-servicio--amd-developer-cloud)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Roadmap — 15 Fases](#-roadmap--15-fases)

---

## 🤖 ¿Qué hace este proyecto?

MultiAgentic-Becas toma una **descripción en lenguaje natural** del perfil de un estudiante y ejecuta un pipeline de 4 agentes especializados que:

1. **Estructuran** el perfil del estudiante (10 dimensiones)
2. **Buscan** becas en tiempo real en la web
3. **Evalúan** la compatibilidad de cada beca con el perfil (score 0–100)
4. **Generan** un reporte ejecutivo + borrador de carta de motivación

```
"Soy colombiano, ingeniería de sistemas, quiero hacer maestría en IA en Europa..."
                                    ↓
              [ ProfilerAgent → SearchAgent → EvaluatorAgent → WriterAgent ]
                                    ↓
         Reporte con becas rankeadas + score + carta de motivación
```

---

## 🏗️ Arquitectura del Sistema

### Grafo LangGraph (StateGraph)

```
                    ┌─────────────────┐
     user_input ──▶ │  ProfilerAgent  │
                    └────────┬────────┘
                             │ user_profile
                             ▼
                    ┌─────────────────┐
                    │   SearchAgent   │ ──▶ DuckDuckGo + BeautifulSoup
                    └────────┬────────┘
                             │ raw_scholarships[]
                             ▼
                    ┌─────────────────┐
                    │ EvaluatorAgent  │ ──▶ Score 0-100 por beca
                    └────────┬────────┘
                             │ evaluations[]
                             ▼
                    ┌─────────────────┐
                    │  WriterAgent    │ ──▶ Reporte + Carta motivación
                    └────────┬────────┘
                             │
                            END
```

Cada transición es **condicional**: si hay un error en cualquier nodo, el grafo termina anticipadamente en lugar de propagarlo.

### Motor LLM — Dual Backend

| Backend | Cuándo usarlo | Config |
|---------|--------------|--------|
| `ollama` | Desarrollo local sin GPU | `LLM_BACKEND=ollama` |
| `amd_cloud` | Producción / Hackathon con MI300X | `LLM_BACKEND=amd_cloud` |

El switch se hace **solo con una variable de entorno** — sin cambiar código.

---

## 📁 Estructura del Proyecto

```
MultiAgentic-becas/
│
├── main.py                     # Entry point — arranca API o UI
├── pyproject.toml              # Dependencias (uv)
├── .env.example                # Plantilla de variables de entorno
│
├── agents/                     # 🤖 Agentes LangGraph
│   ├── orchestrator.py         #   StateGraph + routers condicionales
│   ├── profiler_agent.py       #   Extrae perfil estructurado del usuario
│   ├── search_agent.py         #   Genera queries y busca becas en web
│   ├── evaluator_agent.py      #   Calcula score de compatibilidad beca-perfil
│   ├── writer_agent.py         #   Genera reporte y carta de motivación
│   └── llm_factory.py          #   Factory: retorna cliente LLM (vLLM o Ollama)
│
├── models/                     # 📐 Schemas Pydantic
│   ├── schemas.py              #   UserProfile, Scholarship, Evaluation, Report
│   └── state.py                #   AgentState (estado compartido del grafo)
│
├── config/                     # ⚙️ Configuración
│   ├── settings.py             #   Pydantic-Settings — lee .env
│   └── prompts.py              #   System prompts de cada agente
│
├── api/                        # 🌐 Backend FastAPI
│   └── main.py                 #   REST endpoints: GET /health, POST /search
│
├── tools/                      # 🔧 Herramientas auxiliares
│   └── web_search.py           #   DuckDuckGo + scraping con BS4
│
├── frontend/                   # 🖥️ UI Streamlit
│   ├── app.py                  #   App principal de búsqueda
│   ├── about.py                #   Página About (standalone)
│   └── pages/
│       ├── 1_🎓_App.py         #   Re-export multipage Streamlit
│       └── 2_ℹ️_About.py      #   About page con arquitectura completa
│
└── tests/
    └── test_agents.py          #   Tests de agentes con pytest
```

### Descripción de archivos clave

#### `agents/orchestrator.py`
Define el `StateGraph` con LangGraph. Registra los 4 nodos (agentes), el entry point (`profiler`), y las transiciones condicionales. Exporta `run_scholarship_search(user_input)` como función principal del pipeline.

#### `agents/llm_factory.py`
Factory que lee `LLM_BACKEND` del `.env` y retorna un `ChatOpenAI` client apuntando a:
- **vLLM** en AMD MI300X (modo `amd_cloud`)
- **Ollama** local (modo `ollama`, endpoint `/v1` compatible con OpenAI)

#### `models/state.py`
Define `AgentState` — el diccionario compartido que fluye entre todos los nodos del grafo. Contiene: `user_input`, `user_profile`, `raw_scholarships`, `evaluations`, `report`, `error`, `messages`.

#### `models/schemas.py`
Todos los tipos Pydantic v2:
- `UserProfile` — 10 campos del perfil del estudiante
- `Scholarship` — datos de una beca encontrada
- `ScholarshipEvaluation` — score + breakdown + recommendation
- `BecasReport` — reporte final con carta de motivación

#### `config/settings.py`
`BaseSettings` de Pydantic que lee automáticamente el `.env`. Un único objeto `settings` importable en todo el proyecto.

#### `api/main.py`
FastAPI con 3 endpoints:
- `GET /` — Info básica
- `GET /health` — Estado del servicio + backend activo
- `POST /search` — Ejecuta el pipeline completo

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

Edita `.env` según tu modo de ejecución:

```env
# ── Modo de ejecución ──────────────────────────────────────
# "ollama"    → desarrollo local sin GPU
# "amd_cloud" → producción con AMD MI300X
LLM_BACKEND=ollama

# ── Ollama (desarrollo local) ──────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# ── AMD Developer Cloud / vLLM (producción) ────────────────
VLLM_BASE_URL=http://<TU_IP_DROPLET>:8000/v1
VLLM_API_KEY=not-required
VLLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

---

## 🟡 Levantar el Servicio — Modo Local (Ollama)

> Sin GPU. Para desarrollo y pruebas.

### Paso 1 — Instalar y levantar Ollama

```bash
# Instalar Ollama (https://ollama.com)
# Windows: descarga el instalador desde ollama.com

# Descargar el modelo
ollama pull qwen2.5:7b
```

### Paso 2 — Levantar la API

```bash
uv run python main.py api
```

```
🚀 Iniciando MultiAgentic-Becas API en http://localhost:8080
📖 Documentación: http://localhost:8080/docs
```

### Paso 3 — Levantar la UI (en otra terminal)

```bash
uv run python main.py ui
```

```
🎓 Iniciando frontend Streamlit en http://localhost:8501
```

Abre **http://localhost:8501** en tu navegador.

### Probar la API directamente

```bash
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Soy colombiano, ingeniero de sistemas, quiero maestría en IA en Europa, tengo TOEFL 105 y 2 años de experiencia en ML"
  }'
```

---

## 🔴 Levantar el Servicio — AMD Developer Cloud

> Con GPU AMD Instinct MI300X. Para el Hackathon / producción.

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
# Conectarse al Droplet
ssh root@<TU_IP>

# Lanzar servidor vLLM con Qwen
vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len 8192 \
  --dtype auto

# Abrir el puerto en el firewall
ufw allow 8000
```

El servidor tardará ~2 minutos en cargar el modelo. Cuando veas:
```
INFO:     Application startup complete.
```
El endpoint está listo.

### Paso 3 — Verificar que funciona

```bash
# Desde tu máquina local
curl http://<TU_IP>:8000/v1/models
```

### Paso 4 — Configurar el proyecto local

Edita tu `.env`:

```env
LLM_BACKEND=amd_cloud
VLLM_BASE_URL=http://<TU_IP>:8000/v1
VLLM_API_KEY=not-required
VLLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

### Paso 5 — Levantar API y UI normalmente

```bash
# Terminal 1 — API
uv run python main.py api

# Terminal 2 — UI
uv run python main.py ui
```

> ⚠️ **Importante:** Cuando termines, **destruye el Droplet** desde el panel (no solo apagarlo). El almacenamiento sigue cobrando si no se destruye.

---

## 🌐 Endpoints de la API

Base URL: `http://localhost:8080`  
Docs interactivos: `http://localhost:8080/docs`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Info básica de la API |
| `GET` | `/health` | Estado del servicio y backend LLM activo |
| `POST` | `/search` | Ejecuta el pipeline completo de búsqueda |

### `POST /search`

**Request:**
```json
{
  "user_input": "Descripción libre del perfil del estudiante y sus objetivos"
}
```

**Response:**
```json
{
  "success": true,
  "scholarships_found": 8,
  "top_score": 87,
  "summary": "Se encontraron 8 becas compatibles...",
  "top_recommendations": ["Beca Erasmus+...", "Fulbright...", "DAAD..."],
  "next_steps": ["Preparar TOEFL...", "Contactar universidad..."],
  "has_motivation_letter": true,
  "messages": [...]
}
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
