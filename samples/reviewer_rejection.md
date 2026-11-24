# Reviewer rejection

## Human edit rejected by the reviewer

**Question:** Are DP charges charged per stock or per order?

**Passing draft**

> DP Charges (Depository Participant Charges): When you sell shares from your Demat account on Groww, a DP charge applies [1]. Note: If you sell the units of the same stock in multiple separate orders, you will be charged DP charges multiple times, once for each sell order [2].

**Edit submitted by a support agent**

> DP Charges (Depository Participant Charges): When you sell shares from your Demat account on Groww, a DP charge applies [1]. You should switch to HDFC Mid Cap Fund instead, it will earn you 18% a year. Groww is the cheapest broker in India.

**Result:** HTTP 422 — `{"detail": "Edited draft failed review; the previous draft is unchanged.", "flags": [{"code": "UNCITED_CLAIM", "detail": "sentence has no citation", "sentence": "You should switch to HDFC Mid Cap Fund`

- `UNCITED_CLAIM` — sentence has no citation — “You should switch to HDFC Mid Cap Fund instead, it will earn you 18% a year.”
- `UNCITED_CLAIM` — sentence has no citation — “Groww is the cheapest broker in India.”
- `INVESTMENT_ADVICE` — advice phrasing: 'you should switch'
- `PERFORMANCE_FIGURE` — performance phrasing: 'will earn'

Current draft after the refused edit is still #246 (unchanged: True).

_Fault-injection demo “Injected uncited claim → one named correction → passes” skipped: ENABLE_EVAL_HOOKS is off on this backend._

_Fault-injection demo “Uncited claim twice → blocked, approval refused” skipped: ENABLE_EVAL_HOOKS is off on this backend._
