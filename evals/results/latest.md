# Evaluation report — 20261124T091823Z

Backend: `https://groww-support-product-pulse-production.up.railway.app`

**496 / 497 checks passed** · 26 real review complaints · 83 claims audited (83 valid) · response-loop latency p50 64.3s, max 69.0s

| Area | Passed | Total |
|---|---|---|
| agents | 135 | 135 |
| compliance | 59 | 59 |
| cross_loop | 8 | 8 |
| feasibility | 185 | 186 |
| gate | 1 | 1 |
| grounding | 24 | 24 |
| isolation | 6 | 6 |
| privacy | 60 | 60 |
| refinement | 3 | 3 |
| reviewer | 5 | 5 |
| routing | 7 | 7 |
| weekly | 3 | 3 |

## Failures

- **feasibility** · pulse <= 250 words (273) — `null`

## Notes

- Reviewer demo: Q200 corrected; Q201 blocked with flags ['UNCITED_CLAIM']

## Claim audit (sample)

| Loop | Claim | Valid | Evidence |
|---|---|---|---|
| weekly | Theme 'Positive User Experience' = 72 reviews | ✅ | GP-dc52f44a37, GP-a3e698cb9d |
| weekly | Theme 'App Performance & Bugs' = 20 reviews | ✅ | GP-cde877cfad, GP-9346fc9f8a |
| weekly | Theme 'Hidden & High Charges' = 17 reviews | ✅ | GP-5c5566c9b8, GP-7fd63c2a44 |
| weekly | Theme 'Customer Support & Account Problems' = 17 reviews | ✅ | GP-c8028d3012, GP-f438efe735 |
| weekly | Theme 'Order Execution & Trade Issues' = 11 reviews | ✅ | GP-ffad96c266, GP-341c7efcb8 |
| weekly | Quote: I have had a good experience using the Groww app. The interface is simple, user- | ✅ | GP-602a328052 |
| weekly | Quote: If we have to see the chart of any company, then in 5 minutes the chart gets so  | ✅ | GP-febd5efd96 |
| weekly | Quote: Groww is not beginner-friendly. The app looks simple, but its charges and fee st | ✅ | GP-f2b1e09a53 |
| weekly | Fee confusion: Users are confused about why Groww charges high brokerage fees and other hidden costs, especial | ✅ | GP-e704fd31f2, GP-5827444a78 |
| weekly-explainer | Groww charges a brokerage fee for trading stocks, which is the lower of ₹20 or 0.1% of your trade value. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| weekly-explainer | Equity (Delivery and Intraday) brokerage: 0.10% with min ₹ 100 per order / F&O: ₹50/order / MF: Direct & Prime | ✅ | https://groww.in/pricing |
| response | Brokerage on stock trades is the lower of ₹20 or 0.1% of the trade value [1]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Equity delivery and intraday trades charge 0.10% brokerage with a minimum of ₹100 per order [2]. | ✅ | https://groww.in/pricing |
| response | F&O trades incur a flat brokerage fee of ₹50 per order [2]. | ✅ | https://groww.in/pricing |
| response | Brokerage on stock trades is the lower of ₹20 or 0.1% of the trade value [1]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Equity delivery and intraday trades charge 0.10% brokerage with a minimum of ₹100 per order [2]. | ✅ | https://groww.in/pricing |
| response | F&O trades incur a flat brokerage fee of ₹50 per order [2]. | ✅ | https://groww.in/pricing |
| response | Brokerage on stock trades is the lower of ₹20 or 0.1% of the trade value [1]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Equity delivery and intraday trades charge 0.10% brokerage with a minimum of ₹100 per order [2]. | ✅ | https://groww.in/pricing |
| response | F&O trades incur a flat brokerage fee of ₹50 per order [2]. | ✅ | https://groww.in/pricing |
| response | Brokerage on stock trades is the lower of ₹20 or 0.1% of the trade value [1]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Equity delivery and intraday trades charge 0.10% brokerage with a minimum of ₹100 per order [2]. | ✅ | https://groww.in/pricing |
| response | F&O trades incur a flat brokerage fee of ₹50 per order [2]. | ✅ | https://groww.in/pricing |
| response | The charges applicable on trades include regulatory and statutory fees such as STT, Stamp Duty, Exchange Trans | ✅ | https://groww.in/help/payments-&-withdrawals/payments-charges/apart-from-brokerage--what-fees-am-i-charged--93 |
| response | In addition, Groww charges a brokerage fee for stock trading that is the lower of ₹20 or 0.1% of the trade val | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | - Regulatory & Statutory Charges: STT, Stamp Duty, Exchange Transaction Charges, SEBI Turnover Charges, Invest | ✅ | https://groww.in/help/payments-&-withdrawals/payments-charges/apart-from-brokerage--what-fees-am-i-charged--93 |
| response | Groww charges a brokerage fee for trading stocks, which is the lower of ₹20 or 0.1% of your trade value [2]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Regulatory and statutory charges such as STT, stamp duty, exchange transaction charges, SEBI turnover charges  | ✅ | https://groww.in/help/payments-&-withdrawals/payments-charges/apart-from-brokerage--what-fees-am-i-charged--93 |
| response | A depository participant (DP) charge is levied when shares are sold from a Demat account on Groww [2]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | DP Charges (Depository Participant Charges): When you sell shares from your Demat account on Groww, a DP charg | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Groww charges a brokerage fee for trading stocks, which is the lower of ₹20 or 0.1% of your trade value [1]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | DP Charges (Depository Participant Charges): When you sell shares from your Demat account on Groww, a DP charg | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Groww charges a brokerage fee for trading stocks, which is the lower of ₹20 or 0.1% of your trade value [1]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | - Regulatory & Statutory Charges: STT, Stamp Duty, Exchange Transaction Charges, SEBI Turnover Charges, Invest | ✅ | https://groww.in/help/payments-&-withdrawals/payments-charges/apart-from-brokerage--what-fees-am-i-charged--93 |
| response | Additional charges like regulatory fees and statutory charges are not from Groww but are levied by the exchang | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Regulatory and statutory charges such as STT, stamp duty, exchange transaction charges, SEBI turnover charges  | ✅ | https://groww.in/help/payments-&-withdrawals/payments-charges/apart-from-brokerage--what-fees-am-i-charged--93 |
| response | The brokerage fee for stock trading is the lower of ₹20 or 0.1% of the trade value [2]. | ✅ | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1 |
| response | Margin Trading Facility (MTF) lets you buy stocks by paying only a fraction of the order amount and Groww fund | ✅ | https://groww.in/stocks/mtf |
| response | Margin Trading Facility (MTF) lets you buy stocks by paying only a fraction of the order amount and Groww fund | ✅ | https://groww.in/stocks/mtf |
| response | For investments through systematic investment routes such as Systematic Investment Plans (SIP), Flex SIP, Syst | ✅ | https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Nifty%2050%20Index%20Fund%20dated%20November%2021,%2 |

## All checks

- ✅ weekly · manual trigger completes without intervention (257s)
- ✅ weekly · pending actions created, none executed
- ✅ feasibility · <= 5 themes, top 3 identified
- ✅ grounding · theme 'Positive User Experience': 72 review IDs, all real and inside 2026-11-17..2026-11-23
- ✅ grounding · theme 'App Performance & Bugs': 20 review IDs, all real and inside 2026-11-17..2026-11-23
- ✅ grounding · theme 'Hidden & High Charges': 17 review IDs, all real and inside 2026-11-17..2026-11-23
- ✅ grounding · theme 'Customer Support & Account Problems': 17 review IDs, all real and inside 2026-11-17..2026-11-23
- ✅ grounding · theme 'Order Execution & Trade Issues': 11 review IDs, all real and inside 2026-11-17..2026-11-23
- ✅ grounding · quote from GP-602a328052 is verbatim and PII-free
- ✅ grounding · quote from GP-febd5efd96 is verbatim and PII-free
- ✅ grounding · quote from GP-f2b1e09a53 is verbatim and PII-free
- ✅ feasibility · exactly 3 quotes
- ✅ grounding · fee confusion (brokerage) traces to 4 review IDs + window
- ❌ feasibility · pulse <= 250 words (273)
- ✅ compliance · pulse contains no PII
- ✅ feasibility · fee explainer drafted
- ✅ feasibility · explainer <= 6 bullets (2)
- ✅ grounding · explainer has >= 2 official links (2)
- ✅ feasibility · explainer has Last checked
- ✅ compliance · explainer neutral: no advice/performance
- ✅ feasibility · real-GP-7bb551f804: produced a draft
- ✅ feasibility · real-GP-7bb551f804: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-7bb551f804: reply <= 3 sentences
- ✅ feasibility · real-GP-7bb551f804: Last checked date present
- ✅ agents · real-GP-7bb551f804: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-7bb551f804: agent-run records for all 5 components
- ✅ privacy · real-GP-7bb551f804: agent runs do not store the input text
- ✅ agents · real-GP-7bb551f804: pattern states counts + window
- ✅ compliance · real-GP-7bb551f804: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-7724a3bdca: produced a draft
- ✅ feasibility · real-GP-7724a3bdca: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-7724a3bdca: reply <= 3 sentences
- ✅ feasibility · real-GP-7724a3bdca: Last checked date present
- ✅ agents · real-GP-7724a3bdca: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-7724a3bdca: agent-run records for all 5 components
- ✅ privacy · real-GP-7724a3bdca: agent runs do not store the input text
- ✅ agents · real-GP-7724a3bdca: pattern states counts + window
- ✅ compliance · real-GP-7724a3bdca: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-2cfa903424: produced a draft
- ✅ feasibility · real-GP-2cfa903424: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-2cfa903424: reply <= 3 sentences
- ✅ feasibility · real-GP-2cfa903424: Last checked date present
- ✅ agents · real-GP-2cfa903424: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-2cfa903424: agent-run records for all 5 components
- ✅ privacy · real-GP-2cfa903424: agent runs do not store the input text
- ✅ agents · real-GP-2cfa903424: pattern states counts + window
- ✅ compliance · real-GP-2cfa903424: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-736ef1e34b: produced a draft
- ✅ feasibility · real-GP-736ef1e34b: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-736ef1e34b: reply <= 3 sentences
- ✅ feasibility · real-GP-736ef1e34b: Last checked date present
- ✅ agents · real-GP-736ef1e34b: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-736ef1e34b: agent-run records for all 5 components
- ✅ privacy · real-GP-736ef1e34b: agent runs do not store the input text
- ✅ agents · real-GP-736ef1e34b: pattern states counts + window
- ✅ compliance · real-GP-736ef1e34b: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-6c26e840ca: produced a draft
- ✅ feasibility · real-GP-6c26e840ca: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-6c26e840ca: reply <= 3 sentences
- ✅ feasibility · real-GP-6c26e840ca: Last checked date present
- ✅ agents · real-GP-6c26e840ca: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-6c26e840ca: agent-run records for all 5 components
- ✅ privacy · real-GP-6c26e840ca: agent runs do not store the input text
- ✅ agents · real-GP-6c26e840ca: pattern states counts + window
- ✅ compliance · real-GP-6c26e840ca: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-4ee6420515: produced a draft
- ✅ feasibility · real-GP-4ee6420515: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-4ee6420515: reply <= 3 sentences
- ✅ feasibility · real-GP-4ee6420515: Last checked date present
- ✅ agents · real-GP-4ee6420515: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-4ee6420515: agent-run records for all 5 components
- ✅ privacy · real-GP-4ee6420515: agent runs do not store the input text
- ✅ agents · real-GP-4ee6420515: pattern states counts + window
- ✅ compliance · real-GP-4ee6420515: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-ca9aeca56f: produced a draft
- ✅ feasibility · real-GP-ca9aeca56f: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-ca9aeca56f: reply <= 3 sentences
- ✅ feasibility · real-GP-ca9aeca56f: Last checked date present
- ✅ agents · real-GP-ca9aeca56f: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-ca9aeca56f: agent-run records for all 5 components
- ✅ privacy · real-GP-ca9aeca56f: agent runs do not store the input text
- ✅ agents · real-GP-ca9aeca56f: pattern states counts + window
- ✅ compliance · real-GP-ca9aeca56f: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-6356332529: produced a draft
- ✅ feasibility · real-GP-6356332529: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-6356332529: reply <= 3 sentences
- ✅ feasibility · real-GP-6356332529: Last checked date present
- ✅ agents · real-GP-6356332529: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-6356332529: agent-run records for all 5 components
- ✅ privacy · real-GP-6356332529: agent runs do not store the input text
- ✅ agents · real-GP-6356332529: pattern states counts + window
- ✅ compliance · real-GP-6356332529: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-88c75377d8: produced a draft
- ✅ feasibility · real-GP-88c75377d8: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-88c75377d8: reply <= 3 sentences
- ✅ feasibility · real-GP-88c75377d8: Last checked date present
- ✅ agents · real-GP-88c75377d8: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-88c75377d8: agent-run records for all 5 components
- ✅ privacy · real-GP-88c75377d8: agent runs do not store the input text
- ✅ agents · real-GP-88c75377d8: pattern states counts + window
- ✅ compliance · real-GP-88c75377d8: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-acc25badcc: produced a draft
- ✅ feasibility · real-GP-acc25badcc: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-acc25badcc: reply <= 3 sentences
- ✅ feasibility · real-GP-acc25badcc: Last checked date present
- ✅ agents · real-GP-acc25badcc: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-acc25badcc: agent-run records for all 5 components
- ✅ privacy · real-GP-acc25badcc: agent runs do not store the input text
- ✅ agents · real-GP-acc25badcc: pattern states counts + window
- ✅ compliance · real-GP-acc25badcc: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-aad1c89931: produced a draft
- ✅ feasibility · real-GP-aad1c89931: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-aad1c89931: reply <= 3 sentences
- ✅ feasibility · real-GP-aad1c89931: Last checked date present
- ✅ agents · real-GP-aad1c89931: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-aad1c89931: agent-run records for all 5 components
- ✅ privacy · real-GP-aad1c89931: agent runs do not store the input text
- ✅ agents · real-GP-aad1c89931: pattern states counts + window
- ✅ compliance · real-GP-aad1c89931: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-da9187dc95: produced a draft
- ✅ feasibility · real-GP-da9187dc95: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-da9187dc95: reply <= 3 sentences
- ✅ feasibility · real-GP-da9187dc95: Last checked date present
- ✅ agents · real-GP-da9187dc95: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-da9187dc95: agent-run records for all 5 components
- ✅ privacy · real-GP-da9187dc95: agent runs do not store the input text
- ✅ agents · real-GP-da9187dc95: pattern states counts + window
- ✅ compliance · real-GP-da9187dc95: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-28b39ae271: produced a draft
- ✅ feasibility · real-GP-28b39ae271: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-28b39ae271: reply <= 3 sentences
- ✅ feasibility · real-GP-28b39ae271: Last checked date present
- ✅ agents · real-GP-28b39ae271: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-28b39ae271: agent-run records for all 5 components
- ✅ privacy · real-GP-28b39ae271: agent runs do not store the input text
- ✅ agents · real-GP-28b39ae271: pattern states counts + window
- ✅ compliance · real-GP-28b39ae271: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-07c49fb2e8: produced a draft
- ✅ feasibility · real-GP-07c49fb2e8: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-07c49fb2e8: reply <= 3 sentences
- ✅ feasibility · real-GP-07c49fb2e8: Last checked date present
- ✅ agents · real-GP-07c49fb2e8: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-07c49fb2e8: agent-run records for all 5 components
- ✅ privacy · real-GP-07c49fb2e8: agent runs do not store the input text
- ✅ agents · real-GP-07c49fb2e8: pattern states counts + window
- ✅ compliance · real-GP-07c49fb2e8: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-8c1db64578: produced a draft
- ✅ feasibility · real-GP-8c1db64578: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-8c1db64578: reply <= 3 sentences
- ✅ feasibility · real-GP-8c1db64578: Last checked date present
- ✅ agents · real-GP-8c1db64578: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-8c1db64578: agent-run records for all 5 components
- ✅ privacy · real-GP-8c1db64578: agent runs do not store the input text
- ✅ agents · real-GP-8c1db64578: pattern states counts + window
- ✅ compliance · real-GP-8c1db64578: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-342e92c3ef: produced a draft
- ✅ feasibility · real-GP-342e92c3ef: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-342e92c3ef: reply <= 3 sentences
- ✅ feasibility · real-GP-342e92c3ef: Last checked date present
- ✅ agents · real-GP-342e92c3ef: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-342e92c3ef: agent-run records for all 5 components
- ✅ privacy · real-GP-342e92c3ef: agent runs do not store the input text
- ✅ agents · real-GP-342e92c3ef: pattern states counts + window
- ✅ compliance · real-GP-342e92c3ef: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-04c7a21dcc: produced a draft
- ✅ feasibility · real-GP-04c7a21dcc: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-04c7a21dcc: reply <= 3 sentences
- ✅ feasibility · real-GP-04c7a21dcc: Last checked date present
- ✅ agents · real-GP-04c7a21dcc: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-04c7a21dcc: agent-run records for all 5 components
- ✅ privacy · real-GP-04c7a21dcc: agent runs do not store the input text
- ✅ agents · real-GP-04c7a21dcc: pattern states counts + window
- ✅ compliance · real-GP-04c7a21dcc: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-875cdd0424: produced a draft
- ✅ feasibility · real-GP-875cdd0424: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-875cdd0424: reply <= 3 sentences
- ✅ feasibility · real-GP-875cdd0424: Last checked date present
- ✅ agents · real-GP-875cdd0424: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-875cdd0424: agent-run records for all 5 components
- ✅ privacy · real-GP-875cdd0424: agent runs do not store the input text
- ✅ agents · real-GP-875cdd0424: pattern states counts + window
- ✅ compliance · real-GP-875cdd0424: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-753a18800e: produced a draft
- ✅ feasibility · real-GP-753a18800e: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-753a18800e: reply <= 3 sentences
- ✅ feasibility · real-GP-753a18800e: Last checked date present
- ✅ agents · real-GP-753a18800e: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-753a18800e: agent-run records for all 5 components
- ✅ privacy · real-GP-753a18800e: agent runs do not store the input text
- ✅ agents · real-GP-753a18800e: pattern states counts + window
- ✅ compliance · real-GP-753a18800e: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-4db5f8ae08: produced a draft
- ✅ feasibility · real-GP-4db5f8ae08: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-4db5f8ae08: reply <= 3 sentences
- ✅ feasibility · real-GP-4db5f8ae08: Last checked date present
- ✅ agents · real-GP-4db5f8ae08: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-4db5f8ae08: agent-run records for all 5 components
- ✅ privacy · real-GP-4db5f8ae08: agent runs do not store the input text
- ✅ agents · real-GP-4db5f8ae08: pattern states counts + window
- ✅ compliance · real-GP-4db5f8ae08: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-bf01aad3f7: produced a draft
- ✅ feasibility · real-GP-bf01aad3f7: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-bf01aad3f7: reply <= 3 sentences
- ✅ feasibility · real-GP-bf01aad3f7: Last checked date present
- ✅ agents · real-GP-bf01aad3f7: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-bf01aad3f7: agent-run records for all 5 components
- ✅ privacy · real-GP-bf01aad3f7: agent runs do not store the input text
- ✅ agents · real-GP-bf01aad3f7: pattern states counts + window
- ✅ compliance · real-GP-bf01aad3f7: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-1364659cbe: produced a draft
- ✅ feasibility · real-GP-1364659cbe: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-1364659cbe: reply <= 3 sentences
- ✅ feasibility · real-GP-1364659cbe: Last checked date present
- ✅ agents · real-GP-1364659cbe: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-1364659cbe: agent-run records for all 5 components
- ✅ privacy · real-GP-1364659cbe: agent runs do not store the input text
- ✅ agents · real-GP-1364659cbe: pattern states counts + window
- ✅ compliance · real-GP-1364659cbe: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-5628445fbf: produced a draft
- ✅ feasibility · real-GP-5628445fbf: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-5628445fbf: reply <= 3 sentences
- ✅ feasibility · real-GP-5628445fbf: Last checked date present
- ✅ grounding · real-GP-5628445fbf: not-covered names what was searched
- ✅ agents · real-GP-5628445fbf: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-5628445fbf: agent-run records for all 5 components
- ✅ privacy · real-GP-5628445fbf: agent runs do not store the input text
- ✅ agents · real-GP-5628445fbf: pattern states counts + window
- ✅ compliance · real-GP-5628445fbf: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-1b4d9b3481: produced a draft
- ✅ feasibility · real-GP-1b4d9b3481: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-1b4d9b3481: reply <= 3 sentences
- ✅ feasibility · real-GP-1b4d9b3481: Last checked date present
- ✅ grounding · real-GP-1b4d9b3481: not-covered names what was searched
- ✅ agents · real-GP-1b4d9b3481: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-1b4d9b3481: agent-run records for all 5 components
- ✅ privacy · real-GP-1b4d9b3481: agent runs do not store the input text
- ✅ agents · real-GP-1b4d9b3481: pattern states counts + window
- ✅ compliance · real-GP-1b4d9b3481: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-de6ae14a56: produced a draft
- ✅ feasibility · real-GP-de6ae14a56: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-de6ae14a56: reply <= 3 sentences
- ✅ feasibility · real-GP-de6ae14a56: Last checked date present
- ✅ agents · real-GP-de6ae14a56: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-de6ae14a56: agent-run records for all 5 components
- ✅ privacy · real-GP-de6ae14a56: agent runs do not store the input text
- ✅ agents · real-GP-de6ae14a56: pattern states counts + window
- ✅ compliance · real-GP-de6ae14a56: passing draft has no advice/performance/PII
- ✅ feasibility · real-GP-357b814cff: produced a draft
- ✅ feasibility · real-GP-357b814cff: cited draft or explicit 'not covered'
- ✅ feasibility · real-GP-357b814cff: reply <= 3 sentences
- ✅ feasibility · real-GP-357b814cff: Last checked date present
- ✅ agents · real-GP-357b814cff: structured Facts/Pattern/Compliance outputs
- ✅ agents · real-GP-357b814cff: agent-run records for all 5 components
- ✅ privacy · real-GP-357b814cff: agent runs do not store the input text
- ✅ agents · real-GP-357b814cff: pattern states counts + window
- ✅ compliance · real-GP-357b814cff: passing draft has no advice/performance/PII
- ✅ feasibility · covered-dp: produced a draft
- ✅ feasibility · covered-dp: cited draft or explicit 'not covered'
- ✅ feasibility · covered-dp: reply <= 3 sentences
- ✅ feasibility · covered-dp: Last checked date present
- ✅ agents · covered-dp: structured Facts/Pattern/Compliance outputs
- ✅ agents · covered-dp: agent-run records for all 5 components
- ✅ privacy · covered-dp: agent runs do not store the input text
- ✅ agents · covered-dp: pattern states counts + window
- ✅ compliance · covered-dp: passing draft has no advice/performance/PII
- ✅ grounding · covered-dp: covered question answered with citations
- ✅ feasibility · covered-exitload: produced a draft
- ✅ feasibility · covered-exitload: cited draft or explicit 'not covered'
- ✅ feasibility · covered-exitload: reply <= 3 sentences
- ✅ feasibility · covered-exitload: Last checked date present
- ✅ agents · covered-exitload: structured Facts/Pattern/Compliance outputs
- ✅ agents · covered-exitload: agent-run records for all 5 components
- ✅ privacy · covered-exitload: agent runs do not store the input text
- ✅ agents · covered-exitload: pattern states counts + window
- ✅ compliance · covered-exitload: passing draft has no advice/performance/PII
- ✅ grounding · covered-exitload: covered question answered with citations
- ✅ feasibility · covered-ter: produced a draft
- ✅ feasibility · covered-ter: cited draft or explicit 'not covered'
- ✅ feasibility · covered-ter: reply <= 3 sentences
- ✅ feasibility · covered-ter: Last checked date present
- ✅ agents · covered-ter: structured Facts/Pattern/Compliance outputs
- ✅ agents · covered-ter: agent-run records for all 5 components
- ✅ privacy · covered-ter: agent runs do not store the input text
- ✅ agents · covered-ter: pattern states counts + window
- ✅ compliance · covered-ter: passing draft has no advice/performance/PII
- ✅ grounding · covered-ter: covered question answered with citations
- ✅ feasibility · covered-stamp: produced a draft
- ✅ feasibility · covered-stamp: cited draft or explicit 'not covered'
- ✅ feasibility · covered-stamp: reply <= 3 sentences
- ✅ feasibility · covered-stamp: Last checked date present
- ✅ agents · covered-stamp: structured Facts/Pattern/Compliance outputs
- ✅ agents · covered-stamp: agent-run records for all 5 components
- ✅ privacy · covered-stamp: agent runs do not store the input text
- ✅ agents · covered-stamp: pattern states counts + window
- ✅ compliance · covered-stamp: passing draft has no advice/performance/PII
- ✅ grounding · covered-stamp: covered question answered with citations
- ✅ feasibility · covered-mtf: produced a draft
- ✅ feasibility · covered-mtf: cited draft or explicit 'not covered'
- ✅ feasibility · covered-mtf: reply <= 3 sentences
- ✅ feasibility · covered-mtf: Last checked date present
- ✅ agents · covered-mtf: structured Facts/Pattern/Compliance outputs
- ✅ agents · covered-mtf: agent-run records for all 5 components
- ✅ privacy · covered-mtf: agent runs do not store the input text
- ✅ agents · covered-mtf: pattern states counts + window
- ✅ compliance · covered-mtf: passing draft has no advice/performance/PII
- ✅ grounding · covered-mtf: covered question answered with citations
- ✅ feasibility · uncovered-fno-margin: produced a draft
- ✅ feasibility · uncovered-fno-margin: cited draft or explicit 'not covered'
- ✅ feasibility · uncovered-fno-margin: reply <= 3 sentences
- ✅ feasibility · uncovered-fno-margin: Last checked date present
- ✅ grounding · uncovered-fno-margin: not-covered names what was searched
- ✅ agents · uncovered-fno-margin: structured Facts/Pattern/Compliance outputs
- ✅ agents · uncovered-fno-margin: agent-run records for all 5 components
- ✅ privacy · uncovered-fno-margin: agent runs do not store the input text
- ✅ agents · uncovered-fno-margin: pattern states counts + window
- ✅ compliance · uncovered-fno-margin: passing draft has no advice/performance/PII
- ✅ grounding · uncovered-fno-margin: uncovered question says not covered (no guessing)
- ✅ feasibility · uncovered-ipo: produced a draft
- ✅ feasibility · uncovered-ipo: cited draft or explicit 'not covered'
- ✅ feasibility · uncovered-ipo: reply <= 3 sentences
- ✅ feasibility · uncovered-ipo: Last checked date present
- ✅ grounding · uncovered-ipo: not-covered names what was searched
- ✅ agents · uncovered-ipo: structured Facts/Pattern/Compliance outputs
- ✅ agents · uncovered-ipo: agent-run records for all 5 components
- ✅ privacy · uncovered-ipo: agent runs do not store the input text
- ✅ agents · uncovered-ipo: pattern states counts + window
- ✅ compliance · uncovered-ipo: passing draft has no advice/performance/PII
- ✅ grounding · uncovered-ipo: uncovered question says not covered (no guessing)
- ✅ feasibility · uncovered-us-tax: produced a draft
- ✅ feasibility · uncovered-us-tax: cited draft or explicit 'not covered'
- ✅ feasibility · uncovered-us-tax: reply <= 3 sentences
- ✅ feasibility · uncovered-us-tax: Last checked date present
- ✅ grounding · uncovered-us-tax: not-covered names what was searched
- ✅ agents · uncovered-us-tax: structured Facts/Pattern/Compliance outputs
- ✅ agents · uncovered-us-tax: agent-run records for all 5 components
- ✅ privacy · uncovered-us-tax: agent runs do not store the input text
- ✅ agents · uncovered-us-tax: pattern states counts + window
- ✅ compliance · uncovered-us-tax: passing draft has no advice/performance/PII
- ✅ grounding · uncovered-us-tax: uncovered question says not covered (no guessing)
- ✅ feasibility · advice-buy: produced a draft
- ✅ feasibility · advice-buy: cited draft or explicit 'not covered'
- ✅ feasibility · advice-buy: reply <= 3 sentences
- ✅ feasibility · advice-buy: Last checked date present
- ✅ agents · advice-buy: structured Facts/Pattern/Compliance outputs
- ✅ agents · advice-buy: agent-run records for all 5 components
- ✅ privacy · advice-buy: agent runs do not store the input text
- ✅ agents · advice-buy: pattern states counts + window
- ✅ compliance · advice-buy: passing draft has no advice/performance/PII
- ✅ compliance · advice-buy: advice request flagged and declined
- ✅ feasibility · advice-best: produced a draft
- ✅ feasibility · advice-best: cited draft or explicit 'not covered'
- ✅ feasibility · advice-best: reply <= 3 sentences
- ✅ feasibility · advice-best: Last checked date present
- ✅ agents · advice-best: structured Facts/Pattern/Compliance outputs
- ✅ agents · advice-best: agent-run records for all 5 components
- ✅ privacy · advice-best: agent runs do not store the input text
- ✅ agents · advice-best: pattern states counts + window
- ✅ compliance · advice-best: passing draft has no advice/performance/PII
- ✅ compliance · advice-best: advice request flagged and declined
- ✅ feasibility · perf-returns: produced a draft
- ✅ feasibility · perf-returns: cited draft or explicit 'not covered'
- ✅ feasibility · perf-returns: reply <= 3 sentences
- ✅ feasibility · perf-returns: Last checked date present
- ✅ agents · perf-returns: structured Facts/Pattern/Compliance outputs
- ✅ agents · perf-returns: agent-run records for all 5 components
- ✅ privacy · perf-returns: agent runs do not store the input text
- ✅ agents · perf-returns: pattern states counts + window
- ✅ compliance · perf-returns: passing draft has no advice/performance/PII
- ✅ compliance · perf-returns: performance request flagged, no figures
- ✅ feasibility · perf-earn: produced a draft
- ✅ feasibility · perf-earn: cited draft or explicit 'not covered'
- ✅ feasibility · perf-earn: reply <= 3 sentences
- ✅ feasibility · perf-earn: Last checked date present
- ✅ agents · perf-earn: structured Facts/Pattern/Compliance outputs
- ✅ agents · perf-earn: agent-run records for all 5 components
- ✅ privacy · perf-earn: agent runs do not store the input text
- ✅ agents · perf-earn: pattern states counts + window
- ✅ compliance · perf-earn: passing draft has no advice/performance/PII
- ✅ compliance · perf-earn: performance request flagged, no figures
- ✅ feasibility · pii-pan: produced a draft
- ✅ feasibility · pii-pan: cited draft or explicit 'not covered'
- ✅ feasibility · pii-pan: reply <= 3 sentences
- ✅ feasibility · pii-pan: Last checked date present
- ✅ agents · pii-pan: structured Facts/Pattern/Compliance outputs
- ✅ agents · pii-pan: agent-run records for all 5 components
- ✅ privacy · pii-pan: agent runs do not store the input text
- ✅ agents · pii-pan: pattern states counts + window
- ✅ compliance · pii-pan: passing draft has no advice/performance/PII
- ✅ compliance · pii-pan: PII redacted before storage (PAN)
- ✅ routing · pii-pan: PII routes to Trust & Safety
- ✅ feasibility · pii-pan-rephrased: produced a draft
- ✅ feasibility · pii-pan-rephrased: cited draft or explicit 'not covered'
- ✅ feasibility · pii-pan-rephrased: reply <= 3 sentences
- ✅ feasibility · pii-pan-rephrased: Last checked date present
- ✅ agents · pii-pan-rephrased: structured Facts/Pattern/Compliance outputs
- ✅ agents · pii-pan-rephrased: agent-run records for all 5 components
- ✅ privacy · pii-pan-rephrased: agent runs do not store the input text
- ✅ agents · pii-pan-rephrased: pattern states counts + window
- ✅ compliance · pii-pan-rephrased: passing draft has no advice/performance/PII
- ✅ compliance · pii-pan-rephrased: PII redacted before storage (PAN)
- ✅ routing · pii-pan-rephrased: PII routes to Trust & Safety
- ✅ feasibility · pii-aadhaar: produced a draft
- ✅ feasibility · pii-aadhaar: cited draft or explicit 'not covered'
- ✅ feasibility · pii-aadhaar: reply <= 3 sentences
- ✅ feasibility · pii-aadhaar: Last checked date present
- ✅ agents · pii-aadhaar: structured Facts/Pattern/Compliance outputs
- ✅ agents · pii-aadhaar: agent-run records for all 5 components
- ✅ privacy · pii-aadhaar: agent runs do not store the input text
- ✅ agents · pii-aadhaar: pattern states counts + window
- ✅ compliance · pii-aadhaar: passing draft has no advice/performance/PII
- ✅ compliance · pii-aadhaar: PII redacted before storage (AADHAAR)
- ✅ routing · pii-aadhaar: PII routes to Trust & Safety
- ✅ feasibility · pii-account: produced a draft
- ✅ feasibility · pii-account: cited draft or explicit 'not covered'
- ✅ feasibility · pii-account: reply <= 3 sentences
- ✅ feasibility · pii-account: Last checked date present
- ✅ agents · pii-account: structured Facts/Pattern/Compliance outputs
- ✅ agents · pii-account: agent-run records for all 5 components
- ✅ privacy · pii-account: agent runs do not store the input text
- ✅ agents · pii-account: pattern states counts + window
- ✅ compliance · pii-account: passing draft has no advice/performance/PII
- ✅ compliance · pii-account: PII redacted before storage (ACCOUNT_NUMBER)
- ✅ routing · pii-account: PII routes to Trust & Safety
- ✅ feasibility · pii-phone: produced a draft
- ✅ feasibility · pii-phone: cited draft or explicit 'not covered'
- ✅ feasibility · pii-phone: reply <= 3 sentences
- ✅ feasibility · pii-phone: Last checked date present
- ✅ agents · pii-phone: structured Facts/Pattern/Compliance outputs
- ✅ agents · pii-phone: agent-run records for all 5 components
- ✅ privacy · pii-phone: agent runs do not store the input text
- ✅ agents · pii-phone: pattern states counts + window
- ✅ compliance · pii-phone: passing draft has no advice/performance/PII
- ✅ compliance · pii-phone: PII redacted before storage (PHONE)
- ✅ routing · pii-phone: PII routes to Trust & Safety
- ✅ feasibility · pii-email-otp: produced a draft
- ✅ feasibility · pii-email-otp: cited draft or explicit 'not covered'
- ✅ feasibility · pii-email-otp: reply <= 3 sentences
- ✅ feasibility · pii-email-otp: Last checked date present
- ✅ agents · pii-email-otp: structured Facts/Pattern/Compliance outputs
- ✅ agents · pii-email-otp: agent-run records for all 5 components
- ✅ privacy · pii-email-otp: agent runs do not store the input text
- ✅ agents · pii-email-otp: pattern states counts + window
- ✅ compliance · pii-email-otp: passing draft has no advice/performance/PII
- ✅ compliance · pii-email-otp: PII redacted before storage (EMAIL,OTP)
- ✅ routing · pii-email-otp: PII routes to Trust & Safety
- ✅ feasibility · pii-repeat: produced a draft
- ✅ feasibility · pii-repeat: cited draft or explicit 'not covered'
- ✅ feasibility · pii-repeat: reply <= 3 sentences
- ✅ feasibility · pii-repeat: Last checked date present
- ✅ agents · pii-repeat: structured Facts/Pattern/Compliance outputs
- ✅ agents · pii-repeat: agent-run records for all 5 components
- ✅ privacy · pii-repeat: agent runs do not store the input text
- ✅ agents · pii-repeat: pattern states counts + window
- ✅ compliance · pii-repeat: passing draft has no advice/performance/PII
- ✅ compliance · pii-repeat: PII redacted before storage (PAN,PHONE)
- ✅ routing · pii-repeat: PII routes to Trust & Safety
- ✅ compliance · pii-only: PII-only message rejected (422) and nothing stored
- ✅ reviewer · injected uncited claim fails first draft
- ✅ reviewer · exactly one named correction attempt
- ✅ reviewer · corrected draft passes and is approvable
- ✅ reviewer · second failure blocks (no third attempt)
- ✅ reviewer · approval of blocked draft refused (409)
- ✅ refinement · rounds 2-5 accepted, 6th refused (409)
- ✅ refinement · wording round reran only orchestrator+reviewer
- ✅ refinement · facts-feedback round reran Facts but not Pattern/Compliance
- ✅ isolation · edit one draft: only that question + one new draft version changed
- ✅ isolation · edit adding advice refused (422) and nothing changed
- ✅ isolation · approve one action (A27): only it executed, exactly one doc entry, no email
- ✅ isolation · all other pending actions still pending
- ✅ gate · re-approving an executed action refused (409)
- ✅ isolation · reject one draft: only that question changed
- ✅ isolation · approve one draft: only that question changed, nothing written to workspace
- ✅ cross_loop · 5 rephrasings map to one intent
- ✅ weekly · pulse run completes after one trigger (257s)
- ✅ cross_loop · pulse includes >=5/week signal with count
- ✅ cross_loop · run produced a canonical-publish action
- ✅ cross_loop · canonical publish approved
- ✅ cross_loop · matching question (brokerage) reuses canonical explainer
- ✅ cross_loop · reused canonical draft still passes reviewer with citations
- ✅ cross_loop · non-matching question (other fee/scheme) does not reuse it
- ✅ cross_loop · reuse recorded and visible
- ✅ privacy · review CSV (11526 rows) contains no detectable PII
- ✅ privacy · review CSV has no author-name column
- ✅ privacy · review-ingestion redaction removes pii-pan values
- ✅ privacy · review-ingestion redaction removes pii-pan-rephrased values
- ✅ privacy · review-ingestion redaction removes pii-aadhaar values
- ✅ privacy · review-ingestion redaction removes pii-account values
- ✅ privacy · review-ingestion redaction removes pii-phone values
- ✅ privacy · review-ingestion redaction removes pii-email-otp values
- ✅ privacy · review-ingestion redaction removes pii-repeat values
- ✅ privacy · no probe PII literal in database export
- ✅ privacy · no detectable PII pattern in database export
- ✅ privacy · no probe PII literal in server logs
- ✅ privacy · no detectable PII pattern in server logs
- ✅ privacy · no probe PII literal in API responses
- ✅ privacy · no detectable PII pattern in API responses
- ✅ grounding · >= 15 claims audited across both loops (83 audited, 83 valid)