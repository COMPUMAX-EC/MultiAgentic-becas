# Codex Global Instructions

## Project Scope

Project: LLM Scholarship Search Agent + ScholarBee Web Interface

Current mode:
- Python backend search agent
- Simple web interface for profile/CV input and result display
- Search logic remains in the backend

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

Do not build unrelated frontend, mobile app, PWA, dashboard, landing page, payment system, login, registration, or unrelated visual interface unless explicitly requested.

A simple web interface named ScholarBee is now part of this project.

Codex may modify web files only when the requested task explicitly involves:
- profile input
- PDF/CV upload
- backend API integration
- result display
- progress panel
- frontend result mapping
- ScholarBee visual redesign
- frontend validation or bug fixing

Codex must not expand the web app beyond the requested task.

The current priority is the search agent core and web integration:
- profile understanding
- minimum input validation
- search intent building
- query family generation
- global web search
- source validation
- page reading
- scholarship extraction
- useful link resolution
- compatibility scoring
- dynamic ranking
- result export
- ScholarBee result display

## Active Search Architecture

The active global search architecture is:

1. Profile Understanding
2. Search Intent Builder
3. Query Families Generator
4. Global Web Search Collector
5. Candidate Deduplication
6. Trusted Source Validation
7. Secondary News Guidance
8. Page Reading
9. Scholarship Extraction
10. Useful Link Resolution
11. Compatibility Scoring
12. Dynamic Ranking Database
13. Expansion Loop if results are weak
14. Final Recommended / Less Recommended Output

Codex must work only on the requested step, block, or task.

## Mandatory Minimum Input Rule

Before running any global search, the user must provide at least:

- country or nationality
- language or languages
- scholarship type

If any of these are missing:
- do not run web search
- do not generate global queries
- do not use demo/sample fallback
- return a clear needs_more_information response
- tell the user which fields are missing

## Trusted Source Rule

A scholarship is reliable only if it comes from:

- university
- government
- embassy
- international organization
- recognized foundation
- official company
- verifiable professional association

And it must have a direct link to the official call preferably, or at least the portal/page where the scholarship information is hosted.

Verified news sources may be used only as secondary guidance when reliable direct sources are insufficient.

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

Project control files may be modified only when the user explicitly asks to update Codex/project-control instructions:
- project_control/PROJECT_CONTEXT.md
- project_control/PHASE_PLAN.md
- project_control/MODULE_CONTRACTS.md
- project_control/CHANGELOG_PHASES.md
- project_control/ENGRAM_MEMORY.md
- .codex/instructions.md

If a task seems to require documentation, skip that part and mention it in the final summary as pending.

## Token Saving Rules

Work only on the requested phase, block, or task.

Do not scan the entire repository unless strictly necessary.

Do not perform global refactors unless explicitly requested.

Do not modify unrelated files.

Prefer small, modular changes.

Use existing schemas, patterns, and folder structure.

Avoid long explanations.

Final response must include only:
- files changed
- short summary
- tests/checks run
- how to run/test
- remaining issues

## Code Quality Rules

Keep the project modular.

Use clear function boundaries.

Add error handling where needed.

Prefer deterministic logic for:
- minimum input validation
- typo normalization
- date validation
- URL deduplication
- useful link selection
- score calculation
- cache lookup
- configuration loading

Use the LLM only where reasoning, extraction, classification, or language understanding is needed.

## Search Rules

Do not use demo_profile.json or sample_profile.json as fallback for live search.

Live search must be profile-dependent.

Database/cache reuse is allowed only when search_signature matches.

If no matching cache exists, run live search or fail honestly.

Do not return fake demo/mock results as live search.

## Useful Link Rule

Every final visible scholarship must have display_link.

display_link priority:
1. official_link
2. application_url
3. source_url
4. pdf_url

If no useful URL exists, do not include the scholarship in final visible results.

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

When implementing a module, include minimal tests when needed for validation.

Do not generate long sample datasets.

Do not generate large mock files.

Do not add unnecessary comments.

Do not add unused dependencies.