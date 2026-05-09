# Phase Plan

## Current Development Mode

The original 15 core phases are completed enough for the current prototype.

The project is now in architecture improvement prompts focused on the active global search flow and ScholarBee web integration.

Codex must execute only the requested prompt/block.

---

## Prompt 1 - Minimum Required Input + Profile Understanding + Search Intent Builder
Status: pending

Scope:
- mandatory minimum input validation
- profile understanding
- typo/error normalization
- multilingual handling
- search intent builder
- prevent demo/sample fallback

---

## Prompt 2 - Query Families + Global Web Search + Expansion Loop
Status: pending

Scope:
- query families generator
- global web search collector
- candidate deduplication
- configurable search limits
- expansion loop when results are weak

---

## Prompt 3 - Trusted Source Validation + Untrusted Sources + Secondary News Guidance
Status: pending

Scope:
- trusted source validation
- accepted / accepted_with_warning / rejected
- untrusted sources storage
- avoid revisiting bad domains
- verified news as secondary guidance only

---

## Prompt 4 - Page Reading + Scholarship Extraction + Useful Link Resolution
Status: pending

Scope:
- page reading preservation
- scholarship extraction fields
- official_link/application_url/source_url/pdf_url
- display_link resolution
- exclude final visible results without useful links

---

## Prompt 5 - Compatibility Scoring + Dynamic Ranking + Final Output
Status: pending

Scope:
- point-based compatibility scoring
- dynamic ranking database
- profile_signature
- recommended / less recommended split
- all recommended visible
- maximum 10 less recommended

---

## Prompt 6 - PDF/CV Input
Status: pending

Scope:
- PDF upload support
- backend PDF text extraction
- profile understanding from CV
- manual text has priority over PDF
- minimum input validation after extraction

---

## Prompt 7 - ScholarBee Frontend Redesign
Status: pending

Scope:
- ScholarBee visual identity
- dark theme
- accent color #d5d612
- profile input
- CV upload area
- progress & quick actions panel
- recommended / less recommended result layout

---

## Prompt 8 - Real Pipeline Metrics and Final Validation
Status: pending

Scope:
- real workflow counts
- metrics object
- rejection summary
- frontend progress panel uses backend counts
- final integration validation