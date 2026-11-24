# Five sample questions through the response loop

Generated against `https://groww-support-product-pulse-production.up.railway.app` by `scripts/build_samples.py`.

## Fee question, covered by official sources

**Question (as stored, after redaction):** Why was a DP charge deducted when I sold my shares?

- intent `dp_charges` · fee type `dp_charges` · scheme `None` · PII types []
- status **ready** · draft origin `generated` · reviewer passed

**Draft reply**

> A DP charge is deducted because a DP charge applies when you sell shares from your Demat account on Groww [1][2].

[1] Groww — Groww Help — How much does Groww charge for stocks? — https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1
    · cited text: “DP Charges (Depository Participant Charges): When you sell shares from your Demat account on Groww, a DP charge applies.”
[2] Groww — Groww Help — What are DP charges? — https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-margin/what-are-dp-charges-depository-participant-charges-1
    · cited text: “When you sell shares from your Demat account on Groww, a DP charge is applied.”

Last checked: 2026-11-23

**Routing:** Pricing & Billing (+Product), P1
- Facts: answerable from official sources, but Pattern: rising issue (32 questions in 7 days, 2 reviews in the last 4 weeks of 2026-08-31–2026-11-23). Reply AND escalate to Product.
- pattern=rising: questions 32 this week vs 0 previous; reviews 1 in last 2 weeks vs 1 in prior 2
- facts=covered

**Agent runs:** facts ok (32743 ms), pattern ok (4 ms), compliance ok (442 ms), orchestrator ok (463 ms), reviewer ok (0 ms)

## Scheme-specific question (answer must come from that fund's own KIM)

**Question (as stored, after redaction):** Is there an exit load on HDFC Mid Cap Fund if I redeem within a year?

- intent `exit_load` · fee type `exit_load` · scheme `hdfc_mid_cap` · PII types []
- status **blocked** · draft origin `correction` · reviewer FAILED · flags ['TOO_LONG']

**Draft reply**

> • In respect of each purchase / switch-in of Units, an Exit Load of 1.00% is payable if Units are redeemed/ switched-out within 1 year from the date of allotment [1]. • No Exit Load is payable if Units are redeemed / switched-out after 1 year from the date of allotment [1].

[1] HDFC Mutual Fund — HDFC Mid Cap Fund — Key Information Memorandum (Nov 2025) — https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Mid%20Cap%20Fund%20dated%20November%2021,%202025_1.pdf
    · cited text: “Load Structure Exit Load:”
    · cited text: “• In respect of each purchase / switch-in of Units, an Exit Load of 1.00% is payable if Units are redeemed/ switched-out within 1 year from the date of allotment.”

Last checked: 2026-11-23

**Routing:** Mutual Fund Operations (+Product), P1
- Facts: answerable from official sources, but Pattern: rising issue (12 questions in 7 days, 0 reviews in the last 4 weeks of 2026-08-31–2026-11-23). Reply AND escalate to Product.
- pattern=rising: questions 12 this week vs 0 previous; reviews 0 in last 2 weeks vs 0 in prior 2
- facts=covered

**Agent runs:** facts ok (32057 ms), pattern ok (4 ms), compliance ok (334 ms), orchestrator ok (32746 ms), reviewer ok (0 ms)

## Investment advice request (factual part only, no recommendation)

**Question (as stored, after redaction):** Should I buy HDFC Small Cap Fund now or wait for a correction?

- intent `other` · fee type `None` · scheme `hdfc_small_cap` · PII types []
- status **ready** · draft origin `generated` · reviewer passed

**Draft reply**

> We can share official facts but cannot recommend whether to buy, sell or hold any investment. The scheme is HDFC Small Cap Fund [1].

[1] HDFC Mutual Fund — HDFC Small Cap Fund — Key Information Memorandum (Nov 2025) — https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Small%20Cap%20Fund%20dated%20November%2021,%202025_0.pdf
    · cited text: “Name of Scheme HDFC Small Cap Fund 2.”

Last checked: 2026-11-23

**Routing:** Customer Support (+Product), P2
- Facts: answerable from official sources, but Pattern: recurring issue (17 questions in 7 days, 0 reviews in the last 4 weeks of 2026-08-31–2026-11-23). Reply AND escalate to Product.
- Compliance: advice/performance requested — reply limited to the factual part.
- pattern=recurring: question did not match a known intent; review matching skipped
- facts=covered

**Agent runs:** facts ok (31903 ms), pattern ok (1 ms), compliance ok (156 ms), orchestrator ok (2896 ms), reviewer ok (0 ms)

## Performance request (no return figures)

**Question (as stored, after redaction):** What returns did HDFC Mid Cap Fund give in the last 3 years?

- intent `other` · fee type `None` · scheme `hdfc_mid_cap` · PII types []
- status **ready** · draft origin `generated` · reviewer passed

**Draft reply**

> We cannot share return or performance figures; the scheme's official factsheet is the authoritative place to check them. Our official sources do not cover this question for HDFC Mid Cap Fund, so we have escalated it to the relevant team instead of guessing.


Last checked: 2026-11-23

**Routing:** Customer Support (+—), P2
- Facts: not covered by official corpus, while Pattern shows a repeated issue — corpus gap; ask the owning team for an official answer.
- pattern=recurring: question did not match a known intent; review matching skipped
- facts=not_covered

**Agent runs:** facts ok (32093 ms), pattern ok (3 ms), compliance ok (399 ms), orchestrator ok (0 ms), reviewer ok (0 ms)

## Not covered by the corpus, with PII in the question (redacted, said out loud, escalated)

**Question (as stored, after redaction):** My PAN is [PAN_REDACTED]. How is tax deducted on dividends from US stocks?

- intent `statutory_gst` · fee type `statutory_charges` · scheme `None` · PII types ['PAN']
- status **ready** · draft origin `generated` · reviewer passed

**Draft reply**

> Our official sources do not cover US stocks, so we have escalated it to the relevant team instead of guessing. We have removed personal details you shared; please never share PAN, Aadhaar, account numbers or OTPs in messages.


Last checked: 2026-11-23

**Routing:** Pricing & Billing (+Trust & Safety), P1
- Facts: not covered by official corpus, while Pattern shows a repeated issue — corpus gap; ask the owning team for an official answer.
- customer shared personal data (PAN); redacted before processing
- pattern=rising: questions 18 this week vs 0 previous; reviews 3 in last 2 weeks vs 3 in prior 2
- facts=not_covered

**Agent runs:** facts ok (32031 ms), pattern ok (5 ms), compliance ok (337 ms), orchestrator ok (0 ms), reviewer ok (0 ms)
