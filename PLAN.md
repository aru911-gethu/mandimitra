# PLAN — mandimitra (formerly mandimate)

> Read `AGENTS.md` first. This file is the source of truth for **what is done and what is next**. Update checkboxes and "Last updated" when work lands.

**Last updated:** 2026-09-29 · **Repo:** github.com/aru911-gethu/Mandimate (in sync, clean) · **Path:** `C:\Users\aru91\Documents\Workspace_AI\Projects_Vscode\mandimitra` · **GitHub repo still named `Mandimate`** (rename on GitHub, then `git remote set-url origin https://github.com/aru911-gethu/mandimitra.git`)

## 1. Purpose and use cases

WhatsApp-first order and stock intelligence for Indian FMCG wholesale (mandi / distributor / kirana). Tagline: "Har Jagah, Har Waqt, Mandi in Pocket."

| # | Use case | User | Status |
|---|---|---|---|
| U1 | Retailer sends a messy order (voice note, handwritten list, "10 peti parle g chhota"); it is parsed into structured items | Retailer | **Sub-Agent 1 missing** (tests fake its output) |
| U2 | Resolve items to SKUs and offer substitutes when out of stock, under a programmable policy (same variant other brand, same brand other variant, highest margin, highest stock, balanced) | Retailer + distributor | done (`inventory_graph`, `graph_agent`) |
| U3 | Distributor margin, FSN (fast/slow/non-moving) analytics, reorder-point alerts, revenue recovery from accepted substitutes | Distributor | done (`analytics_service`) |
| U4 | Proactive reorder nudges to retailers; morning briefing to distributor | Both | message building done; **no sending** |
| U5 | WhatsApp interactive messages (lists, quick-confirm buttons) via Meta Cloud API | Both | payload composer done; **no webhook or send client** |

## 2. Tech stack

| Layer | Choice |
|---|---|
| Language | Python (target 3.12) |
| Models | pydantic v2 |
| Graph | NetworkX inventory/substitution graph |
| LLM | LiteLLM + google-genai (Gemini 2.0 Flash default), OpenAI optional |
| API (planned) | FastAPI + uvicorn |
| Channel (planned) | Meta WhatsApp Business Cloud API v21 |
| Config | python-dotenv / pydantic-settings, `.env.example` |
| Packaging | uv (`uv_build`), `src/` layout, `uv.lock` (added 2026-09-29) |
| Tests | pytest, 3 tests in `tests/` (demo-style, few asserts) |

## 3. Architecture

```
[WhatsApp webhook]* ─► Sub-Agent 1 (voice/handwriting parser)* ─► ExtractedRawItem[]
        ─► Sub-Agent 2 GraphResolverAgent ─► FMCGInventoryGraph.find_substitutes / resolve_raw_order (policy) ─► CartSummary
CartSummary ─► WhatsAppPayloadComposer (list / confirm buttons)  ─► [Meta send API]*
AnalyticsService (margins, FSN, ROP, recovery)  ─► distributor morning briefing
ProactiveTriggerService (reorder need) ─► nudge buttons          (* = not built)
data: src/mandimitra/mock_data/seed_fmcg.json (11 products, 5 substitute relations)
```

## 4. Done

- [x] Data models (`models/schemas.py`): policies, raw/resolved items, cart, margins, FSN, ROP alerts, nudges, revenue recovery
- [x] Inventory graph with fuzzy SKU resolution and 5 substitution strategies (`services/inventory_graph.py`, 413 lines)
- [x] Sub-Agent 2 wrapper (`agents/graph_agent.py`)
- [x] Analytics, proactive triggers, WhatsApp payload composer
- [x] Seed data and three demo/test scripts

## 5. Backlog (ordered)

| ID | Pri | Task | Where | Done when |
|---|---|---|---|---|
| MM-01 | done | uv project created: `pyproject.toml`, `.python-version` 3.12, `uv.lock`; `requirements.txt` removed. Run `uv sync` to create `.venv` | root | `uv run pytest` |
| MM-02 | P0 | Tests moved to `tests/` and collected by pytest; **add real assertions** (they mostly print) | `tests/` | each test asserts substitutes, margins, nudges |
| MM-03 | done | README rewritten | `README.md` | - |
| MM-04 | done | Package `app` renamed to `mandimitra` under `src/` | `src/mandimitra/` | - |
| MM-05 | P1 | Build Sub-Agent 1: order parser (text first, then voice via Whisper/Gemini, then image) with Hinglish normalization -> `ExtractedRawItem` | `agents/order_parser.py` | 20 sample messages parsed >= 90% correct |
| MM-06 | P1 | FastAPI app: `/health`, `/webhook` (verify + receive), `/orders` | `api/` | webhook verified by Meta test |
| MM-07 | P1 | WhatsApp client: send messages using composer payloads, retries, signature check | `channels/whatsapp.py` | message delivered in sandbox |
| MM-08 | P1 | Persistence: replace JSON seed with a DB (SQLite dev, Postgres prod) for products, stock, orders, retailers | `store/` | state survives restart |
| MM-09 | P1 | Settings module loading `.env` (PORT, DEBUG, WhatsApp, LLM keys) | `config.py` | no `os.environ` reads elsewhere |
| MM-10 | P1 | Scheduler for nudges and morning briefing (APScheduler or cron container) | `jobs/` | nudge sent at set time |
| MM-11 | P2 | Realistic seed data: 200+ SKUs, multiple distributors, Hindi/Hinglish aliases | `data/` | seed validated by schema test |
| MM-12 | P2 | Dockerfile + compose (api + db), `.dockerignore` | root | `docker compose up` |
| MM-13 | P2 | CI (GitHub Actions: uv, pytest, ruff), LICENSE | `.github/` | green badge |
| MM-14 | P2 | Privacy: retailer phone numbers and orders are personal data; define retention and masking | `docs/` | policy documented |

## 6. Structure and target layout

Done 2026-09-29: `src/` layout, package `mandimitra`, `tests/`, uv files. Still to add as features land:

```
mandimitra/
├── pyproject.toml uv.lock .python-version .env.example .gitignore .dockerignore
├── README.md PLAN.md AGENTS.md
├── Dockerfile compose.yaml                       (MM-12)
├── src/mandimitra/
│   ├── config.py                                 (MM-09)
│   ├── models/  agents/(order_parser.py*, graph_agent.py)  services/
│   ├── channels/ (whatsapp_composer moves here, whatsapp_client.py*)   api/ (app.py*, webhook.py*)
│   └── mock_data/
├── tests/
└── docs/  architecture.md whatsapp-setup.md
```
(* = not built)

Docker-readiness: config from env only; stateless API container plus DB; webhook needs a public HTTPS URL (tunnel in dev).

## 7. Naming (decided)

**mandimitra** ("mandi friend"): keeps the original idea, easy to say, free on PyPI (checked 2026-09-29). Suggested GitHub description: "WhatsApp-first order parsing, stock substitution and margin analytics for Indian FMCG distributors and kirana retailers". Topics: `whatsapp`, `fmcg`, `supply-chain`, `knowledge-graph`, `india`.

## 8. Decisions log

- Two sub-agents: parser (Agent 1) and knowledge-graph resolver (Agent 2), so substitution logic is deterministic and testable without an LLM.
- Substitution is policy-driven so the distributor decides between margin, stock clearance and brand loyalty.
