# AGENTS.md — mandimitra (formerly mandimate; context file for AI assistants)

Read this and `PLAN.md`; avoid re-scanning the tree. Update the module index and PLAN.md checkboxes with every change.

## Commands (project root)

```bash
uv sync                 # creates .venv from uv.lock
uv run pytest           # 3 tests
```

## Conventions

- Substitution logic must stay deterministic and LLM-free (`services/inventory_graph.py`); LLMs are only for parsing (Sub-Agent 1, not built).
- All cross-module data uses pydantic models from `models/schemas.py`.
- Import as `from mandimitra.<pkg>...`; package lives in `src/mandimitra/`.
- Data files load relative to the module (`Path(__file__)`), never absolute paths.
- No secrets in code; keys in `.env` (git-ignored). `.env.example` is the template.

## Module index (`src/mandimitra/`)

| Path | Purpose |
|---|---|
| `models/schemas.py` | `SubstitutionStrategy`, `SubstitutionPolicy`, `ExtractedRawItem`, `SubstituteItem`, `ResolvedItem`, `CartSummary`, margin / FSN / ROP / nudge / revenue-recovery models |
| `services/inventory_graph.py` | `FMCGInventoryGraph`: load seed JSON, fuzzy `resolve_sku`, `find_substitutes` (5 strategies), `resolve_raw_order` |
| `agents/graph_agent.py` | `GraphResolverAgent` (Sub-Agent 2): raw items -> `CartSummary` under a policy |
| `services/analytics_service.py` | product/family margins, FSN classes, distributor ROP alerts, cart analytics, revenue recovery report |
| `services/trigger_service.py` | `ProactiveTriggerService`: reorder-need evaluation, nudge text |
| `services/whatsapp_composer.py` | Meta payload builders: interactive list, quick-confirm buttons, nudge buttons, distributor morning briefing |
| `mock_data/seed_fmcg.json` | 11 products, 5 substitute relations |

Tests (`tests/`): `test_graph_resolver.py`, `test_analytics_triggers.py`, `test_substitution_routing.py` (demo style, few assertions: MM-02).

## Not built (do not assume it exists)

Sub-Agent 1 (voice/handwriting/text order parser), FastAPI app, WhatsApp webhook and send client, config module, database, scheduler, Docker, CI.

## Known gotchas

- Renamed from `mandimate` / package `app` on 2026-09-29; the GitHub repo is still `Mandimate` (rename pending).
- `pyproject` declares fastapi/uvicorn/litellm/google-genai that nothing imports yet.
- No `.venv` yet: run `uv sync`.
