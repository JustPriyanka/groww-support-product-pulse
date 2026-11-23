# Evaluation Plan: Groww Support & Product Intelligence System

Derived from `problemstatement.md` §Evaluation, `architecture.md` (hard rules) and `edge-cases.md`. Like the Zomato eval plan, split into **deterministic** checks (exact pass/fail; any failure is a regression) and **LLM-dependent** checks (contract checks that must hold 100% because code enforces them, plus quality observations recorded honestly).

Runner: `python evals/run_evals.py --base-url <backend>` (default local; final run against the deployed Railway URL). Every run writes `evals/results/<timestamp>/*.json` and a summary to `evals/results/latest.md`, copied to `Docs/eval-results.md`. Failures are recorded, not hidden.

---

## Track A — Deterministic unit tests (`pytest tests/`)

| Area | Examples |
|---|---|
| PII | PAN, Aadhaar with spaces/dashes, `+91` phones, emails, OTP phrasing, labelled account/folio ids, UPI, card, IFSC; negatives: ₹ amounts, years, “1% exit load”, “365 days” |
| Policy | advice phrasing (“should I buy”, “best fund”), performance phrasing (“returns”, “CAGR”); negatives (“expense ratio is 0.7%”) |
| Reviewer | uncited sentence, bad sentence ID, ungrounded number, > 3 sentences, missing “Last checked” |
| Gate | token mismatch, payload hash mismatch, replay |
| Intents | rephrasings map to the same intent |

## Track B — System evals (against running backend)

### 1. Feasibility
- Every queued question (eval queue: ≥ 20 real complaints + probes) yields a draft that is cited **or** explicit “not covered” (with searched terms).
- Every theme in the pulse has review IDs (resolvable in the CSV) and a window.
- Reply ≤ 3 sentences, pulse ≤ 250 words, explainer ≤ 6 bullets + 2 official links + Last checked.
- Manual trigger → run reaches `completed` without further calls; produces pending actions.

### 2. Edit isolation
Snapshot `questions`, `drafts`, `actions`, `canonical_explainers`, workspace docs/emails (via API) → (a) edit one draft, (b) approve one action, (c) reject one draft → snapshot → diff. Pass iff only the targeted rows (and their own new versions / the one MCP artifact) changed.

### 3. Grounding & compliance
- Audit ≥ 15 claims across both loops: each reply citation resolves to a corpus sentence whose URL is in `sources.json`; each pulse theme/quote resolves to review IDs inside the stated window; each explainer bullet resolves to a corpus sentence.
- Probes: unanswerable questions; advice requests; return/performance requests; repeated and rephrased messages with PAN, Aadhaar, account numbers, phone, email, OTP — in the response loop and injected into review text for the weekly loop.
- Leak scan: all API responses, DB dumps (`/api/debug/export` in eval mode), and server log file scanned with `core.pii` + the literal probe values.

### 4. Agent behavior
- ≥ 20 real review complaints through all three agents; verify each structured output validates against its schema, agent-run records exist for facts/pattern/compliance/orchestrator/reviewer, and no record contains raw input.
- Named scenarios: covered question, uncovered question, recurring issue, PII question.
- Reviewer: force a failing first draft (eval-only fault injection header `X-Eval-Fault: uncited`) → exactly one correction; force two failures → `blocked`, approval 409.

### 5. Cross-loop
- Submit 5 rephrased questions of one intent → next pulse run lists the intent with count ≥ 5.
- Approve the canonical-publish action → submit a matching fee question → draft origin `canonical`, reuse recorded; a question about a different scheme/fee does **not** reuse it.

## Metrics recorded

| Metric | Target |
|---|---|
| Drafts cited or explicit not-covered | 100% |
| Hard-rule violations reaching a human-approvable state | 0 |
| PII leaks in API/DB/logs | 0 |
| Claims audited with valid source | ≥ 15, 100% valid |
| Edit isolation unintended changes | 0 |
| p50 response-loop latency | recorded (Groq free tier) |
| Quality notes (LLM wording, theme quality) | recorded qualitatively, including failures |
