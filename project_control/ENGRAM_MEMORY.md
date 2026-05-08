## What

We are building a scholarship search agent with a Python backend and a simple web interface.

The backend receives user profile text or optional CV PDF, normalizes the profile, performs global scholarship search, validates sources, extracts scholarships, matches/ranks results, and returns recommended and less recommended scholarships.

The web displays:
- one profile input area
- optional CV PDF upload
- terminal-like process panel
- recommended scholarships
- less recommended scholarships
- scholarship name + Open button using display_link

## Learn

Codex must work by improvement blocks, not all blocks at once.

Do not return fake demo/mock results as live search.

Search must be profile-dependent.

Database/cache reuse is allowed only when search_signature matches.

Every final result must have display_link.