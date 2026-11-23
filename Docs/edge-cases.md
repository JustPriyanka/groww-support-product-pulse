# Edge Cases: Groww Support & Product Intelligence System

Derived from `architecture.md` and `implementation-plan.md`. Status updated as phases land.

**Status legend:** 🔴 Unhandled · 🟡 Partially handled · 🟢 Handled

---

## 1. Ingress & Privacy

| # | Edge case | Handling | Status |
|---|---|---|---|
| 1.1 | Question contains PAN / Aadhaar / phone / email / account / OTP / card / UPI / IFSC | Redacted before persistence and agent calls; only types stored; Compliance flag + Trust & Safety routing | ⬜ |
| 1.2 | Same PII rephrased (spaces/dashes in Aadhaar, `+91-`, “A/c no.”) | Patterns tolerate separators and labels | ⬜ |
| 1.3 | Input is only PII (“my PAN is ABCDE1234F”) | After redaction < 3 meaningful words → 422 reject, nothing stored | ⬜ |
| 1.4 | Money amounts / dates look like phone or account numbers (₹1,26,000; 2026) | Currency-prefixed and short numbers excluded; ≥ 9 digits treated as identifiers | ⬜ |
| 1.5 | LLM output re-introduces PII | Reviewer `PII_PRESENT` hard failure; DB write guard raises | ⬜ |
| 1.6 | Logs | Text never logged; redacting log filter as second guard; eval greps logs | ⬜ |
| 1.7 | Voice transcript with PII | Same server ingress redaction; raw transcript never sent anywhere except the submit call, and not persisted | ⬜ |

## 2. Facts / Grounding

| # | Edge case | Handling | Status |
|---|---|---|---|
| 2.1 | Question not covered by corpus (e.g. “F&O margin for Nifty options”) | `not_covered` + query terms + sources searched; reply template says so | ⬜ |
| 2.2 | LLM cites a sentence ID that doesn't exist | Dropped by code; if nothing remains → `not_covered` | ⬜ |
| 2.3 | Reply states a number not in the cited source | `UNGROUNDED_NUMBER` | ⬜ |
| 2.4 | Corpus page changed after explainer approval | Hash mismatch → canonical not reused | ⬜ |
| 2.5 | Multiple schemes in one question | Scheme = first match; canonical scheme-specific reuse disabled when ambiguous | ⬜ |

## 3. Compliance

| # | Edge case | Handling | Status |
|---|---|---|---|
| 3.1 | “Should I buy HDFC Small Cap?” | Advice flag; reply gives only factual parts + standard no-advice sentence | ⬜ |
| 3.2 | “What returns did HDFC Mid Cap give in 3 years?” | Performance flag; no figures; points to official factsheet without numbers | ⬜ |
| 3.3 | LLM compliance second opinion disagrees with rules | LLM can add flags, never clear rule flags | ⬜ |
| 3.4 | Expense ratio “%” mistaken for returns | Performance detector keys on return/CAGR/growth words, not on “%” alone | ⬜ |

## 4. Reviewer / Correction / Refinement

| # | Edge case | Handling | Status |
|---|---|---|---|
| 4.1 | First draft fails | One named correction attempt | ⬜ |
| 4.2 | Second draft fails | `blocked`; flags shown; approve returns 409 | ⬜ |
| 4.3 | Human edit adds advice or PII | Edit is re-reviewed; failing edit is rejected with flags, previous draft untouched | ⬜ |
| 4.4 | Sixth refinement request | 409 “refinement limit (5) reached” | ⬜ |
| 4.5 | Approve a draft twice / approve a rejected draft | Idempotent / 409 | ⬜ |

## 5. Weekly Loop

| # | Edge case | Handling | Status |
|---|---|---|---|
| 5.1 | Trigger while a run is in progress | 409 with running run id | ⬜ |
| 5.2 | LLM returns > 5 themes or unknown review IDs | Code caps at 5, drops unknown IDs | ⬜ |
| 5.3 | LLM quote not verbatim | Rejected; next real review sentence used | ⬜ |
| 5.4 | Pulse > 250 words | One regeneration, then deterministic trim of action-idea text; never exceeds | ⬜ |
| 5.5 | Play scraping blocked on Railway | Falls back to committed snapshot; step logged | ⬜ |
| 5.6 | Fee confusion has no corpus coverage | Next fee type with coverage; recorded | ⬜ |
| 5.7 | Groq rate limit / outage mid-run | Retry/backoff; keyword-taxonomy fallback for clustering; run status `failed` with step if drafting impossible | ⬜ |
| 5.8 | Server restart mid-run | Run marked `interrupted` on startup | ⬜ |

## 6. Approval Gate / MCP

| # | Edge case | Handling | Status |
|---|---|---|---|
| 6.1 | Approve with stale payload hash | 409 — must re-review | ⬜ |
| 6.2 | Replay the same token | MCP refuses (action_id unique) | ⬜ |
| 6.3 | Forged token / tampered payload | MCP refuses | ⬜ |
| 6.4 | Approving pulse doc-append also creates the email draft? | No — one action per approval; isolation eval checks | ⬜ |
| 6.5 | Voice says “approve” | Intent `voice_command_blocked`; no endpoint reachable from voice | ⬜ |
| 6.6 | MCP subprocess fails | Action → `failed` with error; can be retried by a new approval | ⬜ |
