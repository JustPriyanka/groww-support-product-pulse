# Architecture: Groww Support & Product Intelligence System

Derived from `problemstatement.md`. Deployment approach inherited from the Zomato recommendation project (FastAPI on Railway, React/Vite/Tailwind on Vercel, `VITE_API_URL` ↔ `ALLOWED_ORIGINS`, `/api/health`, background work so health checks pass), adapted for: scheduled jobs, persistent approval state, MCP actions, and financial-information safeguards.

---

## 1. System Overview

```
                         ┌──────────────────────── Vercel (React + Vite + Tailwind) ─────────────────────────┐
                         │ Queue · Ask (typed / 🎤 in-browser Whisper) · Weekly Pulse · Approvals ·          │
                         │ Canonical Explainers · Sources · Agent Runs                                       │
                         └───────────────────────────────┬───────────────────────────────────────────────────┘
                                                         │ HTTPS JSON  (VITE_API_URL)
┌────────────────────────────────────── Railway (FastAPI, 1 worker, volume at /data) ─────────────────────────────────────┐
│                                                                                                                         │
│  INGRESS GUARD (core/pii.py) — redact before ANY persistence, logging, or LLM call                                     │
│                                                                                                                         │
│  ┌──────── User response loop ────────┐          ┌──────────── Weekly product loop ─────────────┐                       │
│  │ intent + fee/scheme extraction     │          │ APScheduler cron (Mon 09:00 IST) + manual    │                       │
│  │  ┌─────────┬──────────┬──────────┐ │          │ refresh reviews (best effort) → window       │                       │
│  │  │ Facts   │ Pattern  │Compliance│ │ parallel │ → LLM theme clustering (≤5) → top 3 + quotes │                       │
│  │  └────┬────┴────┬─────┴────┬─────┘ │          │ → fee-confusion detection → ≥5/wk signal     │                       │
│  │       └── Orchestrator ────┘       │◀─canon.──│ → pulse (≤250 w) + fee explainer (≤6 bullets)│                       │
│  │            Reviewer (code rules)   │ explainer│ → reviewer → pending actions                 │                       │
│  │   1 named correction → else block  │          └───────────────────────────────────────────────┘                     │
│  └────────────────────────────────────┘                                                                                │
│                                     │ pending actions (exact payload + target shown)                                    │
│                         APPROVAL GATE (per action, HMAC token bound to action_id + payload hash)                       │
│                                     │ stdio                                                                             │
│                       MCP server (mcp_server/server.py): append_doc_entry · create_email_draft · list/read              │
│                       (no send tool exists)  →  /data/workspace.db                                                     │
│                                                                                                                         │
│  SQLite /data/app.db: questions · drafts · agent_runs · pulse_runs · actions · canonical_explainers · reuses           │
│  Static (git): data/corpus (official pages, fetched_at) · data/reviews/groww_reviews.csv (de-identified)              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                         │
                                           Groq: openai/gpt-oss-120b (reasoning), openai/gpt-oss-20b (bulk classification)
```

**Design principle:** the LLM proposes; code decides. Every non-negotiable safeguard (PII, citations, advice/performance, length limits, approval gating) is enforced by deterministic code that the LLM cannot override. Prompts repeat the rules, but passing a check never depends on the model obeying them.

---

## 2. Component Architecture

### 2.1 Project Structure

```
api.py                     FastAPI app (routes, CORS, lifespan: DB init + scheduler)
config.py                  env-based config (python-dotenv), same pattern as Zomato
core/
  pii.py                   regex PII detection/redaction (PAN, Aadhaar, account, OTP, email, phone, card, IFSC, UPI, names)
  policy.py                advice / performance / return detection, length rules, citation rules
  llm.py                   Groq client, JSON mode, retry/backoff, degraded fallback
  db.py                    SQLite schema + helpers (WAL, foreign keys)
  logging_setup.py         log filter that redacts every record; question text is never logged
  corpus.py                load corpus, sentence-level chunks, BM25 retrieval
  reviews.py               load reviews CSV, windows, fee taxonomy, intent taxonomy
  intents.py               deterministic intent / fee type / scheme extraction
agents/
  facts.py                 Facts Agent
  pattern.py               Pattern Agent
  compliance.py            Compliance Agent
  orchestrator.py          combine → reply draft + routing note; canonical reuse
  reviewer.py              hard-failure checks for reply drafts, pulse, explainer
  response_loop.py         parallel run, correction attempt, refinement rounds, agent-run records
pipeline/
  weekly.py                weekly loop (scheduled + manual)
  themes.py                LLM-assisted clustering with code validation
  scheduler.py             APScheduler wiring
actions/
  gate.py                  pending actions, approval tokens, execution via MCP client
  mcp_client.py            stdio MCP client
mcp_server/server.py       MCP server (FastMCP) — the only writer of documents & email drafts
scripts/                   collect_reviews.py, build_corpus.py, build_eval_queue.py
evals/                     run_evals.py + results/
frontend/                  Vite + React + Tailwind
Docs/                      this doc set
```

### 2.2 Component Responsibilities

| Component | Responsibility | LLM? |
|---|---|---|
| Ingress guard | Redact PII from typed/voice text before storage, logs, agents | No |
| Facts Agent | BM25 retrieval → LLM selects supporting sentence IDs → code verifies IDs exist in corpus → facts with URLs, or `not_covered` + what was searched | Yes (selection only) |
| Pattern Agent | Count reviews matching the intent (theme + keyword), weekly series, question frequency 7d vs prior 7d → `recurring` / `rising` / `isolated` | No (deterministic) |
| Compliance Agent | PII types from ingress; advice / performance / return rules; LLM second opinion that can only **add** flags | Rules + LLM |
| Orchestrator | ≤3-sentence facts-only reply with `[n]` citations + “Last checked”; routing note (team, priority, disagreements); canonical reuse | Yes (wording) |
| Reviewer | Hard checks (uncited claim, ungrounded number, advice, performance figure, PII, length, last-checked); one named correction; block | No |
| Weekly loop | Themes, quotes, fee confusion, ≥5/week signal, pulse, explainer, pending actions | Yes |
| Approval gate | One action per approval; HMAC token over `(action_id, payload_sha256)`; idempotent | No |
| MCP server | `append_doc_entry`, `create_email_draft`, `list_documents`, `read_document`, `list_email_drafts`; verifies token; no send | No |

---

## 3. Data Architecture

### 3.1 AMC and schemes (choice)

**HDFC Mutual Fund** — one of India's largest AMCs and among the most-held fund houses on Groww, with detailed public scheme documents (SID/KIM, factsheets) and FAQ pages. Schemes chosen to span the fee/charge questions users actually ask:

| Scheme | Why |
|---|---|
| HDFC Flexi Cap Fund | Flagship, large AUM, common SIP choice |
| HDFC Mid Cap Fund | Very popular on Groww; exit-load/expense questions |
| HDFC Small Cap Fund | Popular; different riskometer; SIP-limit questions |
| HDFC Nifty 50 Index Fund | Low-cost index fund — contrasts expense ratio and exit-load rules |

### 3.2 Official corpus (15–25 pages)

`data/corpus/sources.json` lists every page: `id, url, publisher (HDFC MF | SEBI | AMFI | Groww), title, type, fetched_at (= "Last checked"), sha256`. `scripts/build_corpus.py` fetches each page, extracts text (BeautifulSoup / pypdf), stores `data/corpus/docs/<id>.txt`, and records `fetched_at`. Pages are committed so deployment needs no network fetch. Text is split into **sentences with stable IDs** (`<source_id>#s<n>`) grouped into ~120-word chunks for BM25 retrieval. Only these IDs can be cited; a citation that does not resolve to a corpus sentence is invalid.

### 3.3 Reviews

`scripts/collect_reviews.py` pulls **real public Google Play reviews** of Groww (`com.nextbillion.groww`, en/IN, newest first) for 2026-08-31 → 2026-11-22 (12 weeks). Each review is redacted **in memory** before writing. Stored columns: `review_id` (`GP-` + sha256 prefix of the public Play review id), `play_review_id`, `source`, `source_url` (listing URL + `reviewId=`), `review_date`, `rating`, `text` (redacted), `thumbs_up`, `app_version`, `pii_redacted` (types only), `collected_at`. Author names, avatars and developer replies are never written.

Snapshot: **11,526 reviews**, 1,917 with ≥ 8 words. Only “substantive” reviews (≥ 6 words) enter clustering; short ones (“good app”) still count in rating stats.

### 3.4 Application state (SQLite on Railway volume)

| Table | Key columns |
|---|---|
| `questions` | id, created_at, channel (typed/voice/eval), text_redacted, pii_types, intent, fee_type, scheme, status, round, current_draft_id |
| `drafts` | id, question_id, version, round, attempt (1/2), origin (generated/correction/human_edit/canonical), reply, citations, last_checked, routing, review (flags, passed), facts/pattern/compliance snapshot |
| `agent_runs` | id, question_id, round, agent, status, duration_ms, output_summary (structured, redacted), input_sha256 — never raw input |
| `pulse_runs` | id, trigger (schedule/manual), window, status, steps log, themes, fee_confusion, signals, pulse, explainer, review |
| `actions` | id, kind (doc_append / email_draft / canonical_publish), target, payload, payload_sha256, status (pending/approved/executed/rejected/failed), source_ref, decided_at, result |
| `canonical_explainers` | id, fee_type, scheme_scope, bullets, source_ids, source_hashes, last_checked, approved_action_id |
| `canonical_reuses` | canonical_id, question_id, draft_id, at |

The MCP server keeps its own `workspace.db` (`documents`, `doc_entries`, `email_drafts`) — the backend never writes it directly.

`assert_clean()` runs on every text field before INSERT/UPDATE: a write containing PII raises and is never persisted.

---

## 4. User Response Loop

### 4.1 Request lifecycle

1. `POST /api/questions {text, channel}` → `redact()`; store **only** redacted text + PII types. If nothing meaningful remains after redaction (< 3 words), reject with 422.
2. `intents.classify()` (deterministic keyword taxonomy) → `intent`, `fee_type`, `scheme`. Rephrasings map to the same intent, so frequency counts are stable.
3. `asyncio.gather(facts, pattern, compliance)` — true parallel; each returns a Pydantic model. Each run is recorded in `agent_runs` with duration and a redacted summary.
4. Orchestrator → draft. Reviewer → pass or named flags.
5. On failure: **one** correction attempt named after the flags (e.g. `correction:UNCITED_CLAIM(sentence 2)`), rerunning only the orchestrator (and facts if the flag is grounding-related). Second failure → status `blocked`, flags displayed, approve endpoint returns 409.
6. Human: approve / edit (edited text is re-reviewed; must pass) / reject / refine with feedback (≤5 rounds). Refinement reruns only affected components: wording → orchestrator+reviewer; “add/missing facts” → facts+orchestrator+reviewer; pattern/compliance rerun only when the question text changes.

### 4.2 Structured outputs

```python
FactsOutput:      status: covered|not_covered, facts: [{claim, sentence_ids, source_id, url, title}], searched: {query_terms, sources_considered, top_chunks}, last_checked
PatternOutput:    classification: recurring|rising|isolated, review_count, review_window, weekly_counts, matched_themes, sample_review_ids, question_count_7d, question_count_prev_7d, question_window
ComplianceOutput: pii_types, advice_request, performance_request, flags[], llm_flags[], allowed_scope
Draft:            reply (≤3 sentences), citations [{n, source_id, url, sentence_ids}], last_checked, routing {team, priority, reasons, disagreements[]}
ReviewResult:     passed, flags [{code, detail, sentence}], checks {...}
```

### 4.3 Reviewer hard failures (code)

| Code | Rule |
|---|---|
| `UNCITED_CLAIM` | A reply sentence (other than fixed templates) has no valid `[n]` citation, or the citation does not resolve to a corpus sentence |
| `UNGROUNDED_NUMBER` | A number / % / ₹ amount in a sentence does not appear in its cited source sentences |
| `INVESTMENT_ADVICE` | buy/sell/hold/switch recommendations, “best fund”, “you should invest” |
| `PERFORMANCE_FIGURE` | returns/CAGR/NAV growth figures, “returned x%”, “will earn” |
| `PII_PRESENT` | any `core.pii` hit |
| `TOO_LONG` | > 3 sentences (reply) / > 250 words (pulse) / > 6 bullets (explainer) |
| `MISSING_LAST_CHECKED` / `MISSING_SOURCES` | no “Last checked” date / explainer has < 2 official links |

### 4.4 Routing

| Intent family | Team |
|---|---|
| brokerage, DP, statutory/GST, MTF interest, hidden charges | Pricing & Billing |
| withdrawal, add money, refunds | Payments |
| MF exit load, expense ratio, stamp duty, redemption, SIP | Mutual Fund Operations |
| order execution, app lag, login/OTP | Trading Platform Engineering |
| KYC / account / closure | Onboarding & KYC |
| PII present / fraud allegation | Trust & Safety (always added) |

Priority: P1 if PII present or pattern `rising`; P2 if `recurring`; P3 otherwise. A **disagreement** is recorded whenever agents point in different directions — e.g. Facts `covered` + Pattern `rising` → “answerable from official sources, but a growing product issue: reply AND escalate to Product”; Compliance advice flag + Facts covered → “answer only the factual part”.

---

## 5. Weekly Product Loop

Trigger: APScheduler cron `PULSE_CRON` (default Mon 09:00 Asia/Kolkata) and `POST /api/pulse/run`. Runs in a background thread; steps recorded in `pulse_runs.steps`; no human input until approval.

1. **Refresh reviews** (best effort; Play may block datacenter IPs → falls back to the committed snapshot; recorded).
2. **Window** = 7 days ending at the latest review date ≤ today (configurable `window_days`).
3. **Clustering:** LLM (gpt-oss-20b) proposes ≤5 themes from a sample; reviews are assigned in batches of 40 (JSON `{review_id: theme_id}`); code drops unknown IDs, caps at 5 themes, counts, ranks top 3. Fallback: keyword taxonomy.
4. **Quotes:** 3 real quotes, one per top theme — code verifies each quote is a verbatim substring of a redacted review in the window, PII-free, ≤ 35 words.
5. **Fee confusion:** deterministic fee taxonomy over window reviews → top fee type with corpus coverage; LLM states the confusion; supporting review IDs listed.
6. **Signals:** intents with ≥ 5 questions in the last 7 days (from `questions`) → “asked N times this week”.
7. **Pulse** (gpt-oss-120b, JSON) → rendered markdown; reviewer enforces ≤ 250 words, review-ID traceability, no PII; one regeneration with shorter budget, then hard truncate of action-idea text only.
8. **Fee explainer** from retrieved corpus sentences for that fee type: ≤ 6 neutral bullets, each with a citation, ≥ 2 distinct official links, “Last checked”. Reviewer applies the reply rules (no advice/performance, cited, PII-free).
9. **Pending actions** (each separately approvable): append pulse → doc “Weekly Product Pulse”; email draft → “Product Team (internal list)”; append explainer → doc “Customer Fee Explainers”; publish explainer as canonical.

---

## 6. Loop Connection

- **Question frequency → pulse:** step 5.6. Rephrased questions count together because the key is the deterministic intent, not the raw text.
- **Canonical explainer → replies:** approving `canonical_publish` inserts into `canonical_explainers` with `fee_type`, `scheme_scope` (null = all schemes / platform-wide), `source_ids` and their `sha256`. For a new question, the orchestrator reuses it only when (a) fee type matches, (b) scheme matches (scheme-specific explainer requires the same scheme; platform-wide explainer matches questions without a different scheme), and (c) every source still exists with the same hash. The reused draft goes through the same reviewer. Reuse is logged in `canonical_reuses` and shown in the UI.

---

## 7. Approval-Gated Actions (MCP)

- Every action row stores the exact `payload` and `target` and is shown verbatim in the Approvals screen.
- `POST /api/actions/{id}/approve` body `{payload_sha256, confirm: true}` — must match the stored hash (what you saw is what gets written). Only that action executes.
- Backend mints `token = HMAC_SHA256(APPROVAL_SECRET, action_id + ":" + payload_sha256)` and calls the MCP tool over stdio. The MCP server recomputes the hash from the received payload, verifies the token, and refuses replays (action_id unique in `workspace.db`).
- `create_email_draft` only stores a draft (`status: draft`). There is no send tool.
- Voice input can only fill the question box; approval endpoints are click-only and require the payload hash.

---

## 8. Voice

Browser `MediaRecorder` → decoded 16 kHz PCM in memory → **Whisper (tiny.en) running in the browser** via `@huggingface/transformers` in a Web Worker. Audio never leaves the device and is discarded after transcription. The transcript appears in an editable box; the user must click Submit. The server redacts on arrival; only redacted text is stored. Utterances like “approve …” are detected and answered with “Voice can't approve actions”. Limitation: first use downloads ~40 MB of model weights; English only; accuracy lower than server ASR.

---

## 9. Privacy & Logging

- No raw question text in logs: request logs record ids, intents and PII *types* only. A logging filter runs `redact()` on every record as a second guard.
- `agent_runs` stores `input_sha256` (of redacted input) and redacted structured outputs.
- LLM calls only ever receive redacted text.

---

## 10. Deployment (summary — full detail in `deployment-plan.md`)

Railway: Nixpacks `python312`, `uvicorn api:app --workers 1` (single worker so the in-process scheduler runs once), volume mounted at `/data` (`DATA_DIR`). Vercel: root `frontend/`, `VITE_API_URL`. CORS via `ALLOWED_ORIGINS`.
