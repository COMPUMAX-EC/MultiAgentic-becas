# Engram Memory

## What

We are building a scholarship search agent with a Python backend and the ScholarBee web interface.

The backend receives user profile text or optional CV PDF, validates minimum required input, understands the profile, builds search intent, performs global scholarship search, validates trusted sources, extracts scholarships, resolves useful links, scores compatibility, ranks dynamically, and returns recommended / less recommended scholarships.

The web displays:
- ScholarBee interface
- profile input
- optional CV PDF upload
- progress / quick actions panel
- recommended scholarships
- less recommended scholarships
- scholarship name + Open button using display_link

## Why

The system must be a real agentic scholarship search workflow, not a static demo, mock result, or profile-independent search.

The search must be global, profile-dependent, and efficient enough to avoid wasting processing on profiles that are too general.

## Where

Backend:
- api/
- agent/
- services/
- schemas/
- database/
- rag/
- tools/
- utils/
- config/
- prompts/

Frontend:
- app/
- components/
- lib/
- services/
- types/

Control:
- .codex/instructions.md
- project_control/PROJECT_CONTEXT.md
- project_control/PHASE_PLAN.md
- project_control/MODULE_CONTRACTS.md
- project_control/ENGRAM_MEMORY.md

## Learn

Codex must work by requested prompt/block, not all changes at once.

Mandatory minimum input before global search:
- country or nationality
- language or languages
- scholarship type

If required fields are missing, do not run global search.

Do not return fake demo/mock results as live search.

Do not use demo_profile.json or sample_profile.json as live fallback.

Search must be profile-dependent.

Database/cache reuse is allowed only when search_signature matches.

Trusted scholarship sources:
- university
- government
- embassy
- international organization
- recognized foundation
- official company
- verifiable professional association

Verified news sources are secondary guidance only.

Every final visible result must have display_link.

display_link priority:
1. official_link
2. application_url
3. source_url
4. pdf_url

Active global search flow:
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