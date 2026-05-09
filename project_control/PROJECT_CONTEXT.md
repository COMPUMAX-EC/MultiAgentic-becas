# Project Context

Project: LLM Scholarship Search Agent + ScholarBee

Goal:
Build an AI scholarship search agent that receives a user profile or CV PDF, understands the user's scholarship intent, searches globally for scholarship opportunities, validates trusted sources, extracts scholarship details, scores compatibility, ranks results dynamically, and displays recommended / less recommended scholarships in a simple web interface.

Hackathon track:
AI Agents & Agentic Workflows.

Core model:
Qwen local first.

Current local runtime:
- Runtime/wrapper: Ollama
- Ollama version: 0.23.1.0
- Model: qwen2.5:7b-instruct
- Model ID: 845dbda0ea48
- Model size: 4.7 GB
- Model path: C:\Users\jhona\.ollama\models
- Execution command: ollama run qwen2.5:7b-instruct

Future compatibility:
- AMD Developer Cloud
- vLLM adapter
- Remote inference provider

Current product scope:
- Python backend search agent
- FastAPI integration
- ScholarBee web interface
- Profile text input
- Optional CV/PDF upload
- Progress panel
- Recommended scholarships
- Less recommended scholarships

Current constraints:
- No login
- No registration
- No dashboard beyond the simple ScholarBee interface
- No payment system
- No mobile app
- No PWA
- No n8n
- No unrelated UI
- No documentation generation by Codex unless explicitly requested
- Local-first execution
- Codex must work by requested block/task
- Codex must avoid unnecessary file scanning
- Codex must keep changes focused

Active global search architecture:
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

Mandatory minimum input rule:
Before any global search, the user must provide:
- country or nationality
- language or languages
- scholarship type

If these are missing, the system must not run global web search.

Trusted scholarship source rule:
A scholarship is reliable only if it comes from:
- university
- government
- embassy
- international organization
- recognized foundation
- official company
- verifiable professional association

The result should have a direct link to the official call preferably, or at least the official/traceable portal where the scholarship information is hosted.

Verified news sources:
Verified news, newspapers, magazines, or education portals may be used only as secondary guidance when reliable direct sources are insufficient.

Main implementation approach:
- Python backend
- FastAPI API
- Ollama local inference
- Qwen2.5 7B Instruct
- SQLite first
- JSON/cache files first
- Next.js frontend
- Future PostgreSQL/pgvector compatibility
- Future AMD/vLLM compatibility