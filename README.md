# Groww Support & Product Intelligence System

One customer question, three data sources, one reviewed answer, and a weekly product pulse that a human approves before anything is written anywhere.

- **Live app:** https://groww-support-product-pulse-zv6a.vercel.app (React on Vercel)
- **API:** https://groww-support-product-pulse-production.up.railway.app (FastAPI on Railway; `GET /api/health`)
- **Design docs:** [`Docs/`](Docs): problem statement, architecture, edge cases, eval plan, deployment plan
- **Samples for review:** [`samples/`](samples) (index [below](#samples))

---

## 1. What it does

| Loop | Trigger | Output | Who acts |
|---|---|---|---|
| **User response loop** | A support agent types or speaks a customer question | A ≤ 3-sentence, cited, facts-only reply draft, a routing note (team, priority, why), or an explicit "not covered, escalated" | Support agent approves / edits / rejects / asks for a refinement |
| **Weekly product loop** | Cron every Monday 09:00 IST, or "Run pulse now" | Top themes from real Play Store reviews, verbatim quotes, the fee that confuses users most, a ≤ 250-word pulse, a cited fee explainer, and 4 **pending** actions | Product lead approves each action separately |

The **three data sources** behind every answer:

1. **Official corpus:** 24 pages from Groww, HDFC Mutual Fund, SEBI and AMFI. This is the only thing a reply may state as fact.
2. **Real Google Play reviews:** 11,526 de-identified reviews (31 Aug – 22 Nov 2026), refreshed on each weekly run. These show whether an issue is isolated, recurring or rising.
3. **The question stream itself:** how often the same intent was asked this week vs last week. This feeds the pulse and the routing priority.

---

## 2. Architecture

```
 Vercel: React + Vite + Tailwind
   Ask (typed / 🎤 in-browser Whisper) · Queue · Weekly Pulse · Approvals · Library (sources, explainers, agent runs)
                                   │ HTTPS JSON
 Railway: FastAPI, 1 worker, SQLite on a volume (/data)
   INGRESS GUARD (core/pii.py): redact before any storage, log line or LLM call
   ┌── User response loop ─────────────────┐      ┌── Weekly product loop (pipeline/weekly.py) ──┐
   │ deterministic intent / fee / scheme   │      │ refresh reviews → 7-day window               │
   │ ┌───────┬─────────┬────────────┐      │      │ → LLM themes (≤5, code-validated IDs)        │
   │ │ Facts │ Pattern │ Compliance │ in parallel   │ → verbatim quotes → fee confusion            │
   │ └───┬───┴────┬────┴─────┬──────┘      │◀─────│ → question signals (≥5/week)                 │
   │     └─ Orchestrator ───┘  (canonical  │      │ → pulse ≤250 w + fee explainer ≤6 bullets    │
   │        Reviewer (code rules)  reuse)  │      │ → reviewer → 4 PENDING actions               │
   │  1 named correction → else BLOCKED    │      └──────────────────────────────────────────────┘
   └───────────────────────────────────────┘                     │
                    APPROVAL GATE (actions/gate.py): one action per click,
                    HMAC token bound to action_id + sha256(payload shown on screen)
                                   │ stdio
                    MCP server (mcp_server/server.py): append_doc_entry · create_email_draft
                    · list/read. Verifies the token itself. No send tool exists. → workspace.db
 LLM: Groq openai/gpt-oss-120b (writing) and gpt-oss-20b (bulk classification)
```

**Design rule: the LLM proposes, code decides.** Each safeguard is a deterministic check the model cannot talk its way past:

| Safeguard | Where | What code enforces |
|---|---|---|
| PII never stored, logged or sent to the LLM | `core/pii.py`, `core/db.py` (`assert_clean` on every write), `core/logging_setup.py` | Regex redaction for PAN, Aadhaar, phone, email, OTP, account/folio, card, UPI, IFSC; a write containing PII raises |
| Every factual sentence is cited | `agents/reviewer.py` | `UNCITED_CLAIM` if a sentence lacks `[n]` or `[n]` doesn't resolve to a corpus sentence ID |
| No number the source doesn't contain | `agents/reviewer.py`, `agents/facts.py` | `UNGROUNDED_NUMBER`: every ₹ / % / number must appear in the cited sentence |
| No advice, no performance | `core/policy.py` | `INVESTMENT_ADVICE`, `PERFORMANCE_FIGURE` (prose *and* returns tables) |
| Right fund, right audience | `agents/facts.py` | A question about HDFC Mid Cap never sees other funds' KIMs; NRI / buyback / OFS pricing rows are used only when the question names them |
| Length limits | `agents/reviewer.py`, `pipeline/weekly.py` | Reply ≤ 3 sentences of ≤ 40 words; pulse ≤ 250 words; explainer ≤ 6 bullets, ≥ 2 official links |
| A failed draft can't be approved | `agents/response_loop.py` | One correction attempt, named after the failed rule; a second failure means `blocked` (approve returns 409) |

Full detail: [`Docs/architecture.md`](Docs/architecture.md).

### The three agents

| Agent | Uses the LLM? | Output |
|---|---|---|
| **Facts** (`agents/facts.py`) | Selection only. BM25 retrieves candidate sentences; the LLM picks sentence IDs; code drops invented IDs, wrong-fund/wrong-audience rows, unsupported numbers, advice, performance and > 40-word dumps | `covered` facts with sentence IDs, or `not_covered` + what was searched |
| **Pattern** (`agents/pattern.py`) | No | `isolated` / `recurring` / `rising`, from review matches over 12 weeks and question counts 7d vs prior 7d |
| **Compliance** (`agents/compliance.py`) | Rules first; the LLM can only *add* flags | PII types, advice/performance requests, fraud/security flags |

The **orchestrator** writes the reply from the facts alone, and the routing note from all three. When agents disagree, the system says so in the routing note. For example: "Facts: answerable from official sources, but Pattern: rising issue (29 questions in 7 days). Reply AND escalate to Product."

### Where a language model stops being reliable, and what the system does about it

| Failure we saw | System behaviour |
|---|---|
| Question outside the corpus (US-stock tax, F&O margin, fund returns) | Facts returns `not_covered`; the reply says so in plain words and names the topic; routing flags it as a corpus gap |
| Model cites a sentence that doesn't exist, or a number not in the source | Dropped by code before the orchestrator; caught again by the reviewer |
| Model answers a Mid Cap question from the Nifty 50 KIM, or states the NRI rate as the general rate | Code removes other funds' documents and audience-specific rows from what the model can cite |
| Model pastes a returns table after the "we can't share returns" sentence | `PERFORMANCE_FIGURE` detects returns tables |
| Model pastes a 300-word legal clause as one "sentence" | Facts over 40 words are dropped; the reviewer flags long sentences as `TOO_LONG` |
| Theme clustering invents review IDs | Unknown IDs dropped; each theme count = its verified IDs; quotes must be verbatim substrings of a real review in the window |
| LLM down / rate-limited | Extractive / keyword fallbacks; `/api/health` reports `llm_status` (`ok` / `auth_error` / …) so a degraded run is visible |

---

## 3. Approval gate: where it sits and why there

The gate sits **between the weekly loop and the MCP server**, and between a reply draft and "approved". Nothing leaves the system without a human click on that specific item.

- Each weekly run creates **4 separate pending actions**:
  - append the pulse to the "Weekly Product Pulse" doc
  - create an email draft to the Product Team list
  - append the fee explainer to "Customer Fee Explainers"
  - publish the explainer as a canonical answer
- The Approvals screen shows the **exact payload and target**. Approving sends back `sha256(payload)`. If the stored payload changed since it was displayed, the approval is refused (409).
- The backend mints `HMAC(APPROVAL_SECRET, action_id:payload_sha256)`. The **MCP server recomputes the hash and verifies the token itself**, and refuses replays (`action_id` is unique). The backend has no direct write path to the workspace.
- `create_email_draft` only stores a draft. **There is no send tool**, so even a compromised prompt can't email anyone.
- Voice can only fill the question box. Approval endpoints need a click and the payload hash. A spoken or typed "approve…" is classified as `voice_command_blocked` and answered with "Voice and chat can't approve, reject or send anything".
- The eval's isolation check runs edit / approve-one-action / reject, diffing the database each time. Only the targeted rows change.

Why there: the model is good at drafting and clustering, but it is the component we trust least. So the boundary sits exactly where its output would become visible outside the system (a doc, an email, an answer reused for other customers).

---

## 4. How the two loops connect

1. **Questions → pulse.** Every question is classified into a deterministic intent, so rephrasings count together. Intents asked ≥ 5 times in 7 days appear in the pulse as "Repeated questions".
2. **Pulse → replies.** When the product lead approves "publish as canonical", the fee explainer becomes a canonical answer for that fee type. A later question with the same fee type (and fund scope) reuses it. Reuse requires the same reviewer pass, unchanged source hashes, and no audience-specific rows the question doesn't ask about. Every reuse is logged and shown in the UI.
3. **Reviews → routing.** The Pattern agent counts matching reviews for the question's intent. A question that is answerable *and* rising is answered and escalated to Product.

---

## 5. The fee issue that came out of the reviews

The latest weekly run (17–23 Nov 2026, 750 reviews, 161 substantive) found **brokerage** to be the most confusing fee. Users don't understand why brokerage and "hidden" charges are deducted, especially on F&O. Supporting review IDs include GP-e704fd31f2, GP-5827444a78, GP-5a89dedf4f and GP-7724a3bdca. "Fee Transparency" was also the #3 theme (17 reviews, avg ★2.06).

The fee explainer drafted from official sources:

> - Brokerage is the lower of ₹20 or 0.1% of trade value per stock order. [1]
> - The minimum brokerage charged per order is ₹5. [2]
> - Additional charges include regulatory and statutory fees such as STT, stamp duty, exchange transaction charges, SEBI turnover charges, and Investor Protection Fund Trust charge. [3]
> - A DP charge of ₹20 per ISIN applies for pledge or unpledge orders. [2]
>
> Sources: [1] Groww Help: How much does Groww charge for stocks? · [2] groww.in/pricing · [3] Groww Help: Apart from brokerage, what fees am I charged? · Last checked 2026-11-23

Full pulse, themes, quotes and actions: [`samples/weekly_pulse.md`](samples/weekly_pulse.md).

---

## 6. Sources

AMC: **HDFC Mutual Fund**. Schemes: Flexi Cap, Mid Cap, Small Cap, Nifty 50 Index. Every page was fetched on 2026-11-23 and is stored with its sha256 in [`data/corpus/sources.json`](data/corpus/sources.json). Text is in `data/corpus/docs/`. Each sentence has a stable ID (`<source>#s<n>`), and only those IDs can be cited.

| Publisher | Page |
|---|---|
| Groww | [Pricing: brokerage, DP, statutory](https://groww.in/pricing) · [Pricing: mutual funds](https://groww.in/pricing/mutual-funds) · [MTF](https://groww.in/stocks/mtf) |
| Groww Help | [What are DP charges?](https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-margin/what-are-dp-charges-depository-participant-charges-1) · [When are DP charges levied?](https://groww.in/help/stocks,-f&o,-ipo-&-mtf/searchable/when-are-dp-charges-levied) · [DP per stock or per order?](https://groww.in/help/stocks,-f&o,-ipo-&-mtf/searchable/are-dp-charges-per-stock-or-per-order) · [Fees apart from brokerage](https://groww.in/help/payments-&-withdrawals/payments-charges/apart-from-brokerage--what-fees-am-i-charged--93) · [How much does Groww charge for stocks?](https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1) · [What amount was charged for my order?](https://groww.in/help/stocks,-f&o-&-ipo/order/what-amount-was-charged-for-my-order--86) · [Why did my SIP fail?](https://groww.in/help/mutual-funds/order/why-did-my-sip-installment-fail--36) · [ECS bounce when skipping SIP](https://groww.in/help/mutual-funds/discoverable/will-there-be-ecs-bounce-charges-or-any-penalties-if-i-skip-an-installment--49) · [How do I withdraw money?](https://groww.in/help/my-account/payments/how-do-i-withdraw-money-from-my-groww-account-2) · [When will I get the redeemed amount?](https://groww.in/help/payments-&-withdrawals/payments/when-will-i-get-the-redeemed-amount) |
| HDFC Mutual Fund | KIM (Nov 2025): [Flexi Cap](https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Flexi%20Cap%20Fund%20dated%20November%2021,%202025_1.pdf) · [Mid Cap](https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Mid%20Cap%20Fund%20dated%20November%2021,%202025_1.pdf) · [Small Cap](https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Small%20Cap%20Fund%20dated%20November%2021,%202025_0.pdf) · [Nifty 50 Index](https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Nifty%2050%20Index%20Fund%20dated%20November%2021,%202025.pdf) · [Stamp duty FAQ](https://files.hdfcfund.com/s3fs-public/2020-07/FAQs%20on%20Stamp%20Duty.pdf) |
| SEBI | [Investor charter: depositories & DPs](https://www.sebi.gov.in/sebi_data/attachdocs/may-2024/1716996550779.pdf) · [TER disclosure circular (2018)](https://www.sebi.gov.in/sebi_data/attachdocs/jun-2018/1528207661617.pdf) · [Investor charter: mutual funds](https://investor.sebi.gov.in/pdf/investor-charter/mf_amc_amfi.pdf) |
| AMFI | [Direct vs regular plan](https://www.mutualfundssahihai.com/en/what-direct-plan-regular-plan) · [Scheme expenses](https://www.mutualfundssahihai.com/en/what-are-expenses-incurred-mutual-fund-scheme) · [What are loads?](https://www.mutualfundssahihai.com/en/what-are-loads) |

**Reviews:** [`data/reviews/groww_reviews.csv`](data/reviews/groww_reviews.csv) holds real public Google Play reviews of `com.nextbillion.groww`, collected by `scripts/collect_reviews.py`.
- Text is redacted in memory before writing.
- Author names, avatars and developer replies are never stored.
- `review_id` is a hash of the public review ID.

A 34-row sample from the latest window is in [`samples/reviews_sample.csv`](samples/reviews_sample.csv).

---

## 7. Voice

The 🎤 button on the Ask screen records in the browser. **Whisper tiny.en runs in a Web Worker on the device** (`frontend/src/voice/`), so audio never leaves the machine and is discarded after transcription.
- The transcript lands in an editable box, and the agent must press Submit.
- The server redacts PII on arrival, exactly as for typed text.
- Spoken approval commands are refused.

---

## 8. Setup

**Backend** (Python 3.12):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # set GROQ_API_KEY and APPROVAL_SECRET
.venv/bin/uvicorn api:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend && npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```

**Rebuild data (optional; both are committed):**
- `scripts/build_corpus.py` re-fetches the official pages.
- `scripts/collect_reviews.py` re-pulls reviews.

**Deployment:** Railway (Nixpacks, `uvicorn api:app --workers 1`, volume at `/data`) and Vercel (root `frontend/`). Step by step: [`Docs/deployment-plan.md`](Docs/deployment-plan.md).

| Env var | Purpose |
|---|---|
| `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_FAST_MODEL` | LLM |
| `APPROVAL_SECRET` | HMAC key shared by the gate and the MCP server |
| `DATA_DIR` | SQLite + workspace + logs (`/data` on Railway) |
| `PULSE_CRON`, `PULSE_WINDOW_DAYS`, `REFRESH_REVIEWS_ON_RUN` | Weekly loop |
| `ALLOWED_ORIGINS` | CORS (the Vercel URL) |
| `REVIEWER_PASSCODE` | Optional passcode for approve/edit/reject/run |
| `ENABLE_EVAL_HOOKS` | Eval-only fault injection; keep `false` in production |

---

## 9. Evaluations

**Unit tests:** 70 deterministic tests (PII, policy, reviewer, gate, intents, corpus, review refresh, pulse length):

```bash
.venv/bin/python -m pytest -q
```

**System evals against a running backend:**

```bash
# on the backend: ENABLE_EVAL_HOOKS=true (fault injection + debug export); turn it off afterwards
caffeinate -dis .venv/bin/python -u evals/run_evals.py --base-url https://<backend>
```

The runner pushes 46 questions through the live system: 26 real review complaints plus probes (covered, uncovered, advice, performance, PII in 7 forms). It runs the weekly loop twice and checks:
- feasibility (limits, every question gets a draft or an explicit "not covered")
- edit isolation (database diffs)
- grounding (claims audited back to corpus sentences and review IDs)
- compliance
- reviewer correction and blocking
- refinement rounds (max 5)
- cross-loop reuse
- a PII leak scan of API responses, the database export and server logs

It takes about 1 h 45 min on the Groq free tier. Plan: [`Docs/eval.md`](Docs/eval.md).

**Latest full run against the deployed system** (24 Nov 2026): [`evals/results/latest.md`](evals/results/latest.md)

| Area | Passed |
|---|---|
| agents | 135 / 135 |
| compliance | 59 / 59 |
| cross_loop | 8 / 8 |
| feasibility | 185 / 186 |
| grounding | 24 / 24 (83 / 83 audited claims valid) |
| isolation · privacy · refinement · reviewer · routing · weekly · gate | 6/6 · 60/60 · 3/3 · 5/5 · 7/7 · 3/3 · 1/1 |
| **Total** | **496 / 497** |

The one failure (pulse 273 words > 250) is fixed in `f5001ac`, with tests. That run predates the fixes in `cffb40e`, which were verified on the five sample questions rather than by a full rerun.

### Iteration log: what the evals caught and what changed

| Run / check | What went wrong | Fix |
|---|---|---|
| Deployed eval 1 (498/500) | "Tax on US-stock dividends" answered with Indian STT facts | Facts agent drops facts that don't mention the market asked about (`c214b36`); the reply names that market (`509c682`) |
| Deployed eval 1 | PII scan flagged an "OTP" pattern; it was a log label inside the debug endpoint's JSON | Debug endpoints scanned separately as raw data (`c214b36`) |
| Deployed eval 2 (497/502) | 15 review IDs cited by a pulse vanished from the server | Review refresh rebuilt from the snapshot and dropped earlier refreshes; now it accumulates (`f792e9a`) |
| Deployed eval 3 (496/497) | Pulse 273 words: 11 repeated-question topics, and action ideas cut mid-phrase | Top 5 topics + "+N more", trimmed before action text (`f5001ac`) |
| Reading the sample answers (checks had passed) | Returns table leaked after the "no performance" sentence; a Mid Cap question answered from the Nifty 50 KIM; the NRI brokerage rate stated as the general rate (in 4 canonical explainers reused 23×); 55–319-word document dumps | Performance detector covers tables; other funds' KIMs excluded; NRI/buyback/OFS rows need a matching question (also on canonical reuse); 40-word cap on facts and reply sentences (`cffb40e`) |
| Earlier | DP bullet amounts cited without their condition ("for sale values ≥ ₹100") | Heading/bullet-aware corpus; a cited bullet carries its lead line (`19bf187`) |
| Earlier | Labelled ID numbers in unusual formats escaped redaction | Label-based redaction + a scrub of stored rows (`cf6f3a2`) |

The lesson from the last-but-two row: automated checks verify *contracts* (cited, grounded numbers, no PII). They don't verify that the cited sentence is *the right one*. Reading real outputs found four issues, and each became a new code rule with a regression test.

---

## Samples

| File | What it shows |
|---|---|
| [`samples/sample_questions.md`](samples/sample_questions.md) | Five questions through the response loop: draft, citations with cited text, routing, agent runs (covered fee question, fund-specific exit load, advice request, performance request, PII + uncovered topic) |
| [`samples/reviewer_rejection.md`](samples/reviewer_rejection.md) | A support agent's edit adding advice and a return promise, refused by the reviewer with named flags; previous draft unchanged |
| [`samples/weekly_pulse.md`](samples/weekly_pulse.md) | Latest weekly pulse, themes with review IDs, fee issue, fee explainer, pending actions, run steps |
| [`samples/workspace.md`](samples/workspace.md) | Document entries and the email draft as written by the MCP server after approval |
| [`samples/reviews_sample.csv`](samples/reviews_sample.csv) | 34 de-identified reviews from the latest window |
| [`evals/results/latest.md`](evals/results/latest.md) | Latest full evaluation report |

All except the CSV are regenerated from a live backend with `scripts/build_samples.py --base-url <backend>`.

---

## Known limits

- **Latency:** about 50–65 s median per question on the Groq free tier (tokens-per-minute limits). Agents run in parallel, but the facts call dominates.
- **Coverage is deliberately narrow.** The corpus is 24 pages. Questions about withdrawal timing, SIP details, F&O margin, US stocks, taxes or fund returns often get "not covered, escalated". That's intended behaviour, but it means many real complaints end in escalation.
- **Corpus is a static snapshot** (fetched 23 Nov 2026). There's no automatic re-fetch. Canonical answers stop being reused if a source's hash changes, but only after a manual rebuild.
- **Question signals on the demo deployment are inflated by eval traffic.** The eval asks dozens of fee questions, so "MTF ×29" etc. reflect test runs, not customers.
- **Reviewer checks contracts, not judgement.** It verifies citations, numbers, advice, performance, PII and length. It can't tell whether a correctly cited sentence is the *best* answer, and it doesn't catch typos or awkward phrasing.
- **Audience/fund scoping is rule-based:** a fixed list (NRI, buyback, OFS; the 4 HDFC funds). A new audience-specific page would need a new rule.
- **PII detection is regex-based.** It covers Indian identifiers in common and labelled formats; an unusual format or a bare name in free text can slip through.
- **Review refresh depends on Google Play** accepting requests from Railway's IPs. If blocked, the run logs a warning and uses the committed snapshot.
- **Voice:** English only, ~40 MB model download on first use, less accurate than server-side ASR.
- **Single worker, SQLite.** Fine for a demo and a weekly job, not for many concurrent agents. Auth is an optional shared passcode, not per-user accounts.
- Canonical explainers published before `cffb40e` still contain the NRI rate. They remain in the database but are no longer reused for general questions.
