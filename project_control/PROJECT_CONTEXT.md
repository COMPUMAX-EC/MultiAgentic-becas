# Project Context

Project: LLM Scholarship Search Agent

Goal:
Build a console-first AI agent that receives a user profile, searches for scholarships online, validates sources, extracts requirements, checks deadlines, matches scholarships against the profile, ranks results, and exports structured outputs.

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
AMD Developer Cloud / vLLM adapter when available.

Current constraints:
- No UI
- No mobile app
- No PWA
- No n8n
- No documentation generation by Codex
- Local-first execution
- Console-first workflow
- Codex must work phase-by-phase
- Codex must avoid unnecessary file scanning
- Codex must keep changes minimal

Core architecture:
Profile → Query Generation → Web Search → Source Validation → Page Reading → Extraction → Knowledge Base → RAG/Retrieval → Matching → Ranking → JSON/Markdown Output

Main implementation approach:
- Python
- Ollama local inference
- Qwen2.5 7B Instruct
- SQLite first
- JSON/cache files first
- Future PostgreSQL/pgvector compatibility
- Future AMD/vLLM compatibility

Active development phases:
1. Base project and local CLI
2. Local Qwen integration
3. Profile Intelligence Layer
4. Query Generation Agent
5. Web Search Layer
6. Source Intelligence Layer
7. Page Reading and Cleaning
8. Scholarship Extraction Agent
9. Scholarship Knowledge Base
10. RAG and Retrieval Layer
11. Eligibility and Matching Layer
12. Ranking and Recommendation Layer
13. Refresh and Global Scalability Layer
14. AMD Cloud / vLLM Compatibility
15. Hackathon Technical Demo