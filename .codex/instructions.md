# Codex Global Instructions

## Project Scope

Project: LLM Scholarship Search Agent

Current mode: console-first development.

Main runtime:
- Ollama
- Ollama version: 0.23.1.0
- Local model: qwen2.5:7b-instruct
- Model ID: 845dbda0ea48
- Model size: 4.7 GB
- Model path: C:\Users\jhona\.ollama\models
- Execution command: ollama run qwen2.5:7b-instruct

Future compatibility:
- AMD Developer Cloud
- vLLM runtime adapter
- Remote inference provider

Do not build unrelated frontend, mobile app, PWA, dashboard, landing page, or visual interface unless explicitly requested.

A simple web interface is now part of this project.
Codex may modify web files only when the requested task explicitly involves:
- profile input
- PDF upload
- backend API integration
- result display
- progress panel
- frontend result mapping

The current priority is the search agent core:
- profile parsing
- query generation
- web search
- source validation
- page reading
- scholarship extraction
- knowledge base/cache
- RAG/retrieval
- eligibility matching
- ranking
- result export

## Documentation Rule

Do not create, edit, rewrite, expand, or generate documentation files.

Do not modify:
- README.md
- docs/
- documentation/
- CHANGELOG.md
- CONTRIBUTING.md
- architecture documents
- slide content
- pitch content
- markdown documentation files

Only touch documentation if the user explicitly says:
"Codex, update documentation."

If a task seems to require documentation, skip that part and mention it in the final summary as pending.

## Token Saving Rules

Work only on the requested phase or task.

Do not scan the entire repository unless strictly necessary.

Do not perform global refactors unless explicitly requested.

Do not modify unrelated files.

Prefer small, modular changes.

Use existing schemas, patterns, and folder structure.

Avoid long explanations.

Final response must include only:
- files changed
- short summary
- how to run/test

## Code Quality Rules

Keep the project modular.

Use clear function boundaries.

Add error handling where needed.

Prefer deterministic logic for:
- date validation
- URL deduplication
- score calculation
- cache lookup
- configuration loading

Use the LLM only where reasoning, extraction, classification, or language understanding is needed.

## LLM Provider Rules

Use Ollama as the default local LLM provider.

Default model:
qwen2.5:7b-instruct

The local Qwen client must be designed so the provider can later be switched to:
- AMD Developer Cloud
- vLLM
- another remote inference endpoint

Do not hardcode the model in multiple files.

Read model configuration from environment variables or centralized settings.

Recommended environment variables:
- LLM_PROVIDER=ollama
- OLLAMA_MODEL=qwen2.5:7b-instruct
- OLLAMA_HOST=http://localhost:11434

## Output Rules

When implementing a module, include minimal tests or a minimal runnable example only if requested or necessary for validation.

Do not generate long sample datasets.

Do not generate large mock files.

Do not add unnecessary comments.

Do not add unused dependencies.