# Source Manifest

Every official URL the system uses: **24 official pages** in the answer corpus, plus **1 review source** (Google Play), so **25 URLs** in total. The brief asks for a corpus of 15–25 official public pages (AMC, SEBI, AMFI, and official Groww pages for Groww-specific facts). No blogs, private app screens or model memory are used as evidence.

| Publisher | Pages |
|---|---|
| Groww | 13 |
| HDFC Mutual Fund | 5 |
| SEBI | 3 |
| AMFI | 3 |
| **Total official pages** | **24** |
| Google Play (reviews) | 1 |

- **Fetched:** 2026-11-23. Each page's text is stored in [`docs/`](docs) with its sha256 in [`sources.json`](sources.json). The input list is [`source_list.json`](source_list.json) and the builder is [`scripts/build_corpus.py`](../../scripts/build_corpus.py).
- **Citations:** each sentence has a stable ID (`<source-id>#s<n>`), and replies can cite only those IDs, so nothing outside this list can be cited.
- **AMC and schemes:** HDFC Mutual Fund. Flexi Cap, Mid Cap, Small Cap and Nifty 50 Index.

## Official corpus URLs

| # | Publisher | Title | URL | Topics | Type | Source ID |
|---|---|---|---|---|---|---|
| 1 | Groww | Groww Pricing — brokerage, DP and statutory charges | <https://groww.in/pricing> | brokerage, dp_charges, statutory_charges, mtf_interest, hidden_charges | html | `groww-pricing` |
| 2 | Groww | Groww Pricing — Mutual Funds | <https://groww.in/pricing/mutual-funds> | mutual_funds | html | `groww-pricing-mf` |
| 3 | Groww | Groww Margin Trading Facility (MTF) | <https://groww.in/stocks/mtf> | mtf_interest | html | `groww-mtf` |
| 4 | Groww | Groww Help — What are DP charges? | <https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-margin/what-are-dp-charges-depository-participant-charges-1> | dp_charges | html | `groww-help-dp-charges` |
| 5 | Groww | Groww Help — When are DP charges levied? | <https://groww.in/help/stocks,-f&o,-ipo-&-mtf/searchable/when-are-dp-charges-levied> | dp_charges | html | `groww-help-dp-when-levied` |
| 6 | Groww | Groww Help — Are DP charges per stock or per order? | <https://groww.in/help/stocks,-f&o,-ipo-&-mtf/searchable/are-dp-charges-per-stock-or-per-order> | dp_charges | html | `groww-help-dp-per-order` |
| 7 | Groww | Groww Help — Apart from brokerage, what fees am I charged? | <https://groww.in/help/payments-&-withdrawals/payments-charges/apart-from-brokerage--what-fees-am-i-charged--93> | hidden_charges, statutory_charges, dp_charges | html | `groww-help-fees-besides-brokerage` |
| 8 | Groww | Groww Help — How much does Groww charge for stocks? | <https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1> | brokerage, statutory_charges | html | `groww-help-stock-charges` |
| 9 | Groww | Groww Help — What amount was charged for my order? | <https://groww.in/help/stocks,-f&o-&-ipo/order/what-amount-was-charged-for-my-order--86> | hidden_charges | html | `groww-help-contract-note-charges` |
| 10 | Groww | Groww Help — Why did my SIP instalment fail? | <https://groww.in/help/mutual-funds/order/why-did-my-sip-installment-fail--36> | sip | html | `groww-help-sip-failed` |
| 11 | Groww | Groww Help — ECS bounce charges when skipping an SIP instalment | <https://groww.in/help/mutual-funds/discoverable/will-there-be-ecs-bounce-charges-or-any-penalties-if-i-skip-an-installment--49> | sip | html | `groww-help-sip-skip-ecs` |
| 12 | Groww | Groww Help — How do I withdraw money from my Groww account? | <https://groww.in/help/my-account/payments/how-do-i-withdraw-money-from-my-groww-account-2> | withdrawal | html | `groww-help-withdraw-balance` |
| 13 | Groww | Groww Help — When will I get the redeemed amount? | <https://groww.in/help/payments-&-withdrawals/payments/when-will-i-get-the-redeemed-amount> | mf_redemption | html | `groww-help-mf-redemption-timeline` |
| 14 | HDFC Mutual Fund | HDFC Flexi Cap Fund — Key Information Memorandum (Nov 2025) | <https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Flexi%20Cap%20Fund%20dated%20November%2021,%202025_1.pdf> | hdfc_flexi_cap, exit_load, expense_ratio | pdf | `hdfc-flexicap-kim` |
| 15 | HDFC Mutual Fund | HDFC Mid Cap Fund — Key Information Memorandum (Nov 2025) | <https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Mid%20Cap%20Fund%20dated%20November%2021,%202025_1.pdf> | hdfc_mid_cap, exit_load, expense_ratio | pdf | `hdfc-midcap-kim` |
| 16 | HDFC Mutual Fund | HDFC Small Cap Fund — Key Information Memorandum (Nov 2025) | <https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Small%20Cap%20Fund%20dated%20November%2021,%202025_0.pdf> | hdfc_small_cap, exit_load, expense_ratio | pdf | `hdfc-smallcap-kim` |
| 17 | HDFC Mutual Fund | HDFC Nifty 50 Index Fund — Key Information Memorandum (Nov 2025) | <https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Nifty%2050%20Index%20Fund%20dated%20November%2021,%202025.pdf> | hdfc_nifty50_index, exit_load, expense_ratio | pdf | `hdfc-nifty50-kim` |
| 18 | HDFC Mutual Fund | HDFC Mutual Fund — FAQs on Stamp Duty | <https://files.hdfcfund.com/s3fs-public/2020-07/FAQs%20on%20Stamp%20Duty.pdf> | stamp_duty | pdf | `hdfc-stamp-duty-faq` |
| 19 | SEBI | SEBI — Investor Charter for Depositories and Depository Participants (May 2024) | <https://www.sebi.gov.in/sebi_data/attachdocs/may-2024/1716996550779.pdf> | dp_charges | pdf | `sebi-dp-investor-charter` |
| 20 | SEBI | SEBI Circular — Total Expense Ratio disclosure (Jun 2018) | <https://www.sebi.gov.in/sebi_data/attachdocs/jun-2018/1528207661617.pdf> | expense_ratio | pdf | `sebi-ter-circular-2018` |
| 21 | SEBI | SEBI — Investor Charter for Mutual Funds | <https://investor.sebi.gov.in/pdf/investor-charter/mf_amc_amfi.pdf> | mutual_funds | pdf | `sebi-mf-investor-charter` |
| 22 | AMFI | AMFI (Mutual Funds Sahi Hai) — Direct plan vs regular plan | <https://www.mutualfundssahihai.com/en/what-direct-plan-regular-plan> | expense_ratio | html | `amfi-direct-vs-regular` |
| 23 | AMFI | AMFI (Mutual Funds Sahi Hai) — Expenses incurred by a mutual fund scheme | <https://www.mutualfundssahihai.com/en/what-are-expenses-incurred-mutual-fund-scheme> | expense_ratio | html | `amfi-expenses` |
| 24 | AMFI | AMFI (Mutual Funds Sahi Hai) — What are loads? | <https://www.mutualfundssahihai.com/en/what-are-loads> | exit_load | html | `amfi-exit-load` |

## Review source

| # | Source | URL | What was collected |
|---|---|---|---|
| 25 | Google Play: Groww app (`com.nextbillion.groww`) | <https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN> | 11,526 real public reviews, 2026-08-31 → 2026-11-22, collected by [`scripts/collect_reviews.py`](../../scripts/collect_reviews.py) into [`data/reviews/groww_reviews.csv`](../reviews/groww_reviews.csv). PII removed before saving and no author names kept. Each row keeps its own review URL (`&reviewId=…`) and a stable review ID (`GP-…`). |

## Plain-text URL list

```
https://groww.in/pricing
https://groww.in/pricing/mutual-funds
https://groww.in/stocks/mtf
https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-margin/what-are-dp-charges-depository-participant-charges-1
https://groww.in/help/stocks,-f&o,-ipo-&-mtf/searchable/when-are-dp-charges-levied
https://groww.in/help/stocks,-f&o,-ipo-&-mtf/searchable/are-dp-charges-per-stock-or-per-order
https://groww.in/help/payments-&-withdrawals/payments-charges/apart-from-brokerage--what-fees-am-i-charged--93
https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1
https://groww.in/help/stocks,-f&o-&-ipo/order/what-amount-was-charged-for-my-order--86
https://groww.in/help/mutual-funds/order/why-did-my-sip-installment-fail--36
https://groww.in/help/mutual-funds/discoverable/will-there-be-ecs-bounce-charges-or-any-penalties-if-i-skip-an-installment--49
https://groww.in/help/my-account/payments/how-do-i-withdraw-money-from-my-groww-account-2
https://groww.in/help/payments-&-withdrawals/payments/when-will-i-get-the-redeemed-amount
https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Flexi%20Cap%20Fund%20dated%20November%2021,%202025_1.pdf
https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Mid%20Cap%20Fund%20dated%20November%2021,%202025_1.pdf
https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Small%20Cap%20Fund%20dated%20November%2021,%202025_0.pdf
https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Nifty%2050%20Index%20Fund%20dated%20November%2021,%202025.pdf
https://files.hdfcfund.com/s3fs-public/2020-07/FAQs%20on%20Stamp%20Duty.pdf
https://www.sebi.gov.in/sebi_data/attachdocs/may-2024/1716996550779.pdf
https://www.sebi.gov.in/sebi_data/attachdocs/jun-2018/1528207661617.pdf
https://investor.sebi.gov.in/pdf/investor-charter/mf_amc_amfi.pdf
https://www.mutualfundssahihai.com/en/what-direct-plan-regular-plan
https://www.mutualfundssahihai.com/en/what-are-expenses-incurred-mutual-fund-scheme
https://www.mutualfundssahihai.com/en/what-are-loads
https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN
```

*Generated by [`scripts/build_source_manifest.py`](../../scripts/build_source_manifest.py) from `sources.json`.*
