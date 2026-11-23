# Problem Statement: Groww Support & Product Intelligence System

Build and deploy an AI-powered support and product intelligence system for **Groww**, from scratch.

## Problem

Groww support may answer the same fee question repeatedly, while product teams see review trends without knowing which official facts resolve the confusion. Build one system that connects **official mutual fund information**, **recent public reviews**, and **incoming user questions**. It must produce grounded support drafts and a weekly product update, while keeping every consequential action under human control.

## Deployment approach

Follow the workflow of the prior Zomato recommendation project (docs-first: problem statement → architecture → implementation plan → edge cases → eval → deployment plan; FastAPI backend on **Railway**, React/Vite frontend on **Vercel**, `VITE_API_URL` + `ALLOWED_ORIGINS` wiring). Adapt it for scheduled jobs, persistent approval state, MCP actions, and financial-information safeguards. Verify both deployed services work together through the public frontend link.

## Source data

1. One AMC and 3–5 of its mutual fund schemes (choice explained).
2. A corpus of 15–25 official public pages (AMC, SEBI, AMFI; official Groww pages for Groww-specific facts). No blogs, private app screens, or model memory as evidence.
3. A CSV of real, publicly available Groww reviews from the last 8–12 weeks, with dates, source URLs, stable review IDs, and personal information removed before saving. No invented reviews; report gaps plainly.
4. A queue of user questions, including at least 20 real complaints drawn from the review data.

## Weekly product loop (scheduled + manual trigger)

- Cluster reviews into ≤5 themes; top 3 with counts, time window, supporting review IDs, and 3 real de-identified quotes.
- Identify one recurring fee/charge confusion from the reviews.
- Weekly pulse ≤250 words: top themes, evidence, main observation, three product action ideas.
- Customer-facing fee explainer ≤6 bullets, neutral, two official source links, "Last checked" date.
- Show the evidence behind both drafts before approval. Publishing waits for approval.

## User response loop

For each typed or spoken question, run three specialist agents **in parallel** with structured outputs:

- **Facts Agent** — corpus retrieval with citation links; "not covered" + what was searched when absent; never general knowledge.
- **Pattern Agent** — review themes + recent question frequency; recurring / rising / isolated with counts and a time window.
- **Compliance Agent** — PII, investment-advice requests, performance/return requests → policy flags.

An orchestrator produces a facts-only reply draft (≤3 sentences, citation, "Last checked") plus an internal routing note (team, priority), preserving important disagreements. A reviewer checks the draft: uncited factual claim, investment advice, performance figure, or surviving PII = hard failure. One named correction attempt; if the second draft fails, show flags and disable approval. Human may approve, edit, or reject a passing draft. Max five refinement rounds, rerunning only the affected components; record which agents ran without logging sensitive input.

## Connection between the loops

- Same question/intent ≥5 times in one week → signal + count in the weekly pulse.
- An approved fee explainer becomes the **canonical answer** for matching questions (fee, scheme, and source coverage must match), still passing citation and compliance checks.

## Voice

Microphone input with transcript review before submission; voice never approves anything; no raw audio or unredacted transcripts persisted; privacy-compatible transcription; limitations documented.

## Approval-gated actions

Self-contained document and email-draft workflow (no Google account). Genuine MCP tool actions. Before each document append or email-draft creation, show exactly what will be written and where; approve that specific action only. Never auto-send email.

UI: question queue, weekly pulse view, sources panel, approval screen per pending action, canonical explainer view with reuse.

## Non-negotiable safeguards (code and prompts)

Facts only in customer replies; every official claim linked to the corpus; review observations trace to review IDs + window; say so when the corpus cannot answer; no PII (PAN, Aadhaar, account number, OTP, email, phone, …) in stored data, UI, logs, or agent state; public sources only; length limits enforced.

## Evaluation

1. Feasibility · 2. Edit isolation · 3. Grounding & compliance (≥15 claims, PII/advice/return probes, log inspection) · 4. Agent behavior (≥20 real complaints) · 5. Cross-loop behavior. Record failures and improvements.

## Deliverables

Deployed app link + GitHub repo; README (architecture, setup, sources, approval boundaries, loop connection, fee issue, eval results, limitations); de-identified reviews CSV, source list, five sample Q&A drafts, weekly pulse, fee explainer, appended document entry, email draft; a demo path.
