# Implementation Plan: Groww Support & Product Intelligence System

Derived from `problemstatement.md` (requirements) and `architecture.md` (design). Same format as the Zomato project's plan: each phase lists its goal, deliverables, and status.

**Status legend:** ✅ Done · 🟡 Partial · ⬜ Not started

---

## Phase 0 — Scaffolding
**Goal:** Project skeleton, config, environment management (Zomato conventions).
- ⬜ `config.py` (python-dotenv), `.env.example`, `requirements.txt`, `.gitignore`, `nixpacks.toml`, `Procfile`, `.python-version`
- ⬜ `core/logging_setup.py` redacting log filter

## Phase 1 — Source Data
**Goal:** Real, official, de-identified inputs.
- ⬜ `core/pii.py` redactor (needed before any review is written)
- ⬜ `scripts/collect_reviews.py` → `data/reviews/groww_reviews.csv` (12 weeks, Google Play)
- ⬜ Official corpus: 15–25 verified URLs → `scripts/build_corpus.py` → `data/corpus/`
- ⬜ `scripts/build_eval_queue.py` → `data/eval_queue.json` (≥ 20 real complaints from reviews + scripted probes)

## Phase 2 — Core Services
**Goal:** Deterministic building blocks the agents rely on.
- ⬜ `core/db.py` schema + write guard (`assert_clean`)
- ⬜ `core/corpus.py` sentence IDs + BM25
- ⬜ `core/reviews.py`, `core/intents.py` (intent / fee type / scheme taxonomy)
- ⬜ `core/policy.py` advice / performance / citation / length rules
- ⬜ `core/llm.py` Groq JSON calls with retry/backoff + degraded fallback

## Phase 3 — Response Loop Agents
**Goal:** Three parallel specialists + orchestrator + reviewer.
- ⬜ Facts, Pattern, Compliance agents with Pydantic outputs
- ⬜ Orchestrator (reply + routing + disagreements + canonical reuse)
- ⬜ Reviewer + one named correction + block
- ⬜ Human edit / approve / reject / refine (≤ 5 rounds, affected components only) + agent-run records

## Phase 4 — Weekly Loop
**Goal:** Scheduled + manual analysis that ends in pending actions.
- ⬜ Theme clustering (≤ 5), top 3, quotes, review IDs, window
- ⬜ Fee-confusion detection, ≥ 5/week question signal
- ⬜ Pulse (≤ 250 words), fee explainer (≤ 6 bullets, 2 links, last checked) + reviewer
- ⬜ APScheduler cron + manual trigger + run status

## Phase 5 — Approval Gate + MCP
**Goal:** Every write is a separately approved, exactly-previewed MCP tool call.
- ⬜ `mcp_server/server.py` (FastMCP, stdio) with token verification + replay protection, no send tool
- ⬜ `actions/gate.py` + `actions/mcp_client.py`
- ⬜ Canonical publish → `canonical_explainers`; reuse in orchestrator

## Phase 6 — API
- ⬜ `api.py` routes: health, questions, drafts (approve/edit/reject/refine), pulse (run/latest/runs), actions (list/approve/reject), canonical, sources, agent-runs, workspace (docs/email drafts), stats

## Phase 7 — React Web UI
- ⬜ Queue, Ask (typed + voice), Weekly Pulse, Approvals, Canonical, Sources, Workspace, Agent runs
- ⬜ Voice: in-browser Whisper worker, transcript review, “voice can't approve”

## Phase 8 — Testing & Evaluation
- ⬜ `tests/` unit tests (pii, policy, reviewer, gate, intents)
- ⬜ `evals/run_evals.py` — feasibility, edit isolation, grounding & compliance, agent behavior, cross-loop
- ⬜ Results saved to `evals/results/` + `Docs/eval-results.md`

## Phase 9 — Deployment
- ⬜ Railway backend with volume, Vercel frontend, CORS wiring, smoke test through public frontend
- ⬜ Evaluations re-run against the deployed backend

## Phase 10 — Deliverables
- ⬜ README, `deliverables/` (reviews sample, source list, 5 sample Q&As, pulse, explainer, doc entry, email draft), demo path

---

## Build Order
0 → 1 → 2 → 3 → 5 → 4 → 6 → 7 → 8 → 9 → 10 (the gate is built before the weekly loop so that the loop's outputs have somewhere safe to go).
