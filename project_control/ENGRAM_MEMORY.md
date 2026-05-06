# Engram Memory

## Purpose

This file stores the active operational memory of the project using the Engram structure:

- What: what is being built or what changed
- Why: why this decision exists
- Where: where it lives in the repository
- Learn: what Codex or the developer should remember for future phases

This file must stay short.
Do not turn this file into documentation.
Do not duplicate full implementation details.
Only keep active decisions that affect future development.

---

# Global Engram

## What

We are building a console-first LLM Scholarship Search Agent.

The agent receives a user profile, generates intelligent scholarship search queries, searches the web, validates sources, reads pages, extracts scholarship data, stores reusable knowledge, retrieves relevant context, matches scholarships against the user profile, ranks results, and exports structured outputs.

## Why

The project must satisfy the AI Agents & Agentic Workflows track by showing an end-to-end agentic workflow, not a simple RAG system or static scholarship database.

The system must work locally first because AMD Developer Cloud access is not currently available.

## Where

Core project structure:

- agent/
- llm/
- tools/
- schemas/
- services/
- database/
- rag/
- config/
- data/
- utils/
- tests/

Control files:

- .codex/instructions.md
- project_control/PROJECT_CONTEXT.md
- project_control/PHASE_PLAN.md
- project_control/MODULE_CONTRACTS.md
- project_control/CHANGELOG_PHASES.md
- project_control/ENGRAM_MEMORY.md

## Learn

Codex must work phase-by-phase.

Codex must not build UI, mobile app, PWA, dashboard, or frontend.

Codex must not create or edit documentation.

Documentation is handled outside Codex.

Codex must keep changes minimal and avoid global refactors.

The default local model is qwen2.5:7b-instruct running through Ollama.

---

# Runtime Engram

## What

The project uses Qwen locally through Ollama.

## Why

Local execution is required because AMD Developer Cloud credits/access are not available yet.

## Where

Runtime information:

- Runtime/wrapper: Ollama
- Ollama version: 0.23.1.0
- Model: qwen2.5:7b-instruct
- Model ID: 845dbda0ea48
- Model size: 4.7 GB
- Model path: C:\Users\jhona\.ollama\models
- Execution command: ollama run qwen2.5:7b-instruct

## Learn

The LLM provider must be abstracted.

Do not hardcode the model in multiple files.

Use centralized settings or environment variables.

Future providers may include AMD Developer Cloud or vLLM.

---

# Phase Engram Template

Use this template after each completed phase or important subtask.

## Phase X - Phase Name

### What

Short description of what was implemented.

### Why

Short reason for the implementation decision.

### Where

Files or folders affected.

### Learn

Important lesson, constraint, or decision that future phases must respect.

---

# Active Phase Engram

## Phase

Phase 13 - Refresh and Global Scalability Layer

## What

RefreshService updates known scholarship records locally.

## Why

The project needs an incremental local refresh step so known scholarships can age gracefully before any future scheduled global refresh exists.

## Where

- services/refresh_service.py
- schemas/refresh_schema.py
- database/repository.py
- tools/date_validator.py
- main.py

## Learn

Refresh is incremental and deterministic. No full global search, Qwen, cloud, matching, ranking, or RAG changes are used in this phase.
