# MandiMitra

> **Har Jagah, Har Waqt, Mandi in Pocket.**
> WhatsApp-first order and stock intelligence for Indian FMCG distributors and retailers.

A retailer messages an order the way they always do ("10 peti parle g chhota"). MandiMitra turns it into a clean cart, swaps out-of-stock items for the best substitute according to the distributor's own policy, and tells the distributor where margin and stock are leaking.

> Status: core logic (substitution graph, analytics, triggers, WhatsApp message builders) works with mock data. The order parser, WhatsApp webhook and persistence are not built yet. See [PLAN.md](PLAN.md).

## What it does

| Capability | Detail |
|---|---|
| Entity resolution | Fuzzy match of raw item text to SKUs in an inventory knowledge graph |
| Programmable substitution | Per category: same variant other brand, same brand other variant, highest margin, highest stock, or balanced mix |
| Distributor analytics | Product and family margins, fast/slow/non-moving (FSN) SKUs, reorder-point alerts, revenue recovered by accepted substitutes |
| Proactive triggers | Reorder nudges to retailers, morning briefing for the distributor |
| WhatsApp payloads | Meta Cloud API interactive lists and quick-confirm buttons |

## Quick start

```bash
git clone https://github.com/aru911-gethu/Mandimate.git mandimitra   # repo rename pending
cd mandimitra
cp .env.example .env
uv sync
uv run pytest
```

## Configuration

Copy `.env.example` to `.env`: LLM keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `DEFAULT_LLM_MODEL`), WhatsApp Cloud API (`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`), app (`PORT`, `DEBUG`).

## Layout

```
src/mandimitra/
├── agents/graph_agent.py       Sub-Agent 2: resolve items and substitutes
├── models/schemas.py           pydantic data contracts
├── services/                   inventory_graph, analytics_service, trigger_service, whatsapp_composer
└── mock_data/seed_fmcg.json    sample products and substitute relations
tests/                          graph resolver, analytics + triggers, substitution routing
```

## Roadmap

1. ~~uv project, pytest suite, package rename~~ (done)
2. Sub-Agent 1: order parser (text, then voice, then image; Hinglish aware)
3. FastAPI webhook + WhatsApp send client
4. Database, scheduler for nudges and briefings, Docker

Full plan in [PLAN.md](PLAN.md); AI/contributor context in [AGENTS.md](AGENTS.md).

## License

To be decided.
