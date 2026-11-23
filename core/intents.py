"""
Deterministic intent / fee-type / scheme extraction.

Why deterministic: question-frequency counts ("asked 5 times this week") and canonical
answer matching must be stable and auditable. Rephrasings ("why DP charge on sell?",
"what is this depository fee deducted when selling shares") map to the same intent key.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# (intent, team, fee_type or None, patterns) — order = priority (most specific first)
INTENTS: list[tuple[str, str, str | None, list[str]]] = [
    ("voice_command_blocked", "—", None, [r"^\s*(?:please\s+)?(?:approve|reject|publish|send|confirm|delete)\b"]),
    ("exit_load", "Mutual Fund Operations", "exit_load", [r"exit\s*load", r"redemption\s+(?:charge|fee|penalty)", r"charge.{0,20}(?:redeem|redemption)", r"penalty.{0,20}(?:redeem|early|before)"]),
    ("expense_ratio", "Mutual Fund Operations", "expense_ratio", [r"expense\s*ratio", r"\bter\b", r"total expense", r"fund management (?:fee|charge)", r"annual (?:fee|charge).{0,20}(?:fund|scheme)"]),
    ("stamp_duty_mf", "Mutual Fund Operations", "stamp_duty", [r"stamp\s*duty.{0,40}(?:mutual|fund|sip|units?|mf)", r"(?:mutual|fund|sip|units?|mf).{0,40}stamp\s*duty", r"(?:fewer|less)\s+units"]),
    ("dp_charges", "Pricing & Billing", "dp_charges", [r"\bdp\s*(?:charge|fee)s?", r"depository\s*(?:participant\s*)?(?:charge|fee)", r"(?:charge|fee|deduct)\w*.{0,40}\b(?:sell|sold|selling)\b", r"\b(?:sell|sold|selling)\b.{0,40}(?:charge|fee|deduct)"]),
    ("mtf_interest", "Pricing & Billing", "mtf_interest", [r"\bmtf\b", r"margin trad", r"pledge", r"interest.{0,20}(?:negative|balance|margin)"]),
    ("statutory_gst", "Pricing & Billing", "statutory_charges", [r"\bgst\b", r"\bstt\b", r"stamp\s*duty", r"exchange\s+(?:transaction\s+)?charge", r"sebi\s+(?:turnover\s+)?fee", r"\btax(?:es)?\b.{0,30}(?:charge|deduct|trade)"]),
    ("brokerage", "Pricing & Billing", "brokerage", [r"brok[ea]r+a?ge", r"broker\s+charge", r"commission", r"per\s+order", r"₹\s?20\b.{0,20}order", r"\b20\s*(?:rs|rupees?)\b.{0,20}order"]),
    ("hidden_charges", "Pricing & Billing", "hidden_charges", [r"hidden\s+(?:charge|fee|cost)", r"extra\s+charge", r"(?:too\s+(?:much|many)|high|so\s+many|heavy|unknown|unnecessary)\s+charges?", r"charges?\s+(?:are|is)\s+(?:very\s+)?high", r"deduct\w*\s+(?:extra|money|amount)"]),
    ("sip_failure", "Mutual Fund Operations", None, [r"sip.{0,30}(?:fail|bounce|missed|not\s+(?:debited|processed|deducted))", r"(?:mandate|autopay|auto\s*pay|e-?mandate|nach)", r"bounce\s+charge"]),
    ("mf_redemption", "Mutual Fund Operations", None, [r"\bredeem", r"redemption", r"(?:sell|withdraw).{0,20}mutual\s*fund", r"mutual\s*fund.{0,30}(?:sell|withdraw|money\s+back)"]),
    ("withdrawal", "Payments", None, [r"withdraw", r"payout", r"(?:money|amount|funds?)\s+(?:not\s+)?(?:credited|received|stuck|transferred)", r"add(?:ing)?\s+money", r"refund"]),
    ("order_execution", "Trading Platform Engineering", None, [r"order.{0,30}(?:not\s+)?(?:execut|placed|reject|stuck|pending|delay)", r"\b(?:lag|lagging|hang|freez|crash|slow|glitch|not\s+loading|server)", r"\bgtt\b", r"stop\s*loss"]),
    ("kyc_account", "Onboarding & KYC", None, [r"\bkyc\b", r"account\s+(?:open|clos|block|frozen|freez|deactivat|activat)", r"(?:open|close|delete)\w*\s+(?:my\s+)?(?:demat\s+)?account", r"\blogin\b", r"\botp\b"]),
    ("customer_support", "Customer Support", None, [r"customer\s*(?:care|support|service)", r"\bsupport\b", r"no\s+(?:response|reply)", r"\bticket\b", r"complain"]),
    ("fno", "Trading Platform Engineering", None, [r"\bf\s*&\s*o\b", r"\bfno\b", r"\boptions?\b", r"futures?"]),
    ("ipo", "Trading Platform Engineering", None, [r"\bipo\b"]),
    ("us_stocks", "Payments", None, [r"us\s+stock", r"\bus\s+market"]),
]

SCHEMES = {
    "hdfc_flexi_cap": [r"flexi\s*-?\s*cap"],
    "hdfc_mid_cap": [r"mid\s*-?\s*cap"],
    "hdfc_small_cap": [r"small\s*-?\s*cap"],
    "hdfc_nifty50_index": [r"nifty\s*50\s*index", r"nifty\s*index", r"index\s+fund"],
}
SCHEME_NAMES = {
    "hdfc_flexi_cap": "HDFC Flexi Cap Fund",
    "hdfc_mid_cap": "HDFC Mid Cap Fund",
    "hdfc_small_cap": "HDFC Small Cap Fund",
    "hdfc_nifty50_index": "HDFC Nifty 50 Index Fund",
}
FEE_TYPE_LABELS = {
    "dp_charges": "DP (depository) charges on selling shares",
    "brokerage": "brokerage charges",
    "statutory_charges": "statutory charges (GST, STT, stamp duty, exchange fees)",
    "mtf_interest": "MTF (margin trading) interest",
    "exit_load": "mutual fund exit load",
    "expense_ratio": "mutual fund expense ratio",
    "stamp_duty": "stamp duty on mutual fund purchases",
    "hidden_charges": "charges deducted on trades that users call 'hidden'",
}
INTENT_LABELS = {
    "exit_load": "mutual fund exit load", "expense_ratio": "mutual fund expense ratio", "stamp_duty_mf": "stamp duty on mutual funds",
    "dp_charges": "DP charges", "mtf_interest": "MTF interest", "statutory_gst": "GST and statutory charges",
    "brokerage": "brokerage", "hidden_charges": "charges on trades", "sip_failure": "SIP instalment failures",
    "mf_redemption": "mutual fund redemptions", "withdrawal": "withdrawals and payments", "order_execution": "order execution and app performance",
    "kyc_account": "KYC and account access", "customer_support": "customer support response", "fno": "F&O margin and trading rules",
    "ipo": "IPO applications and allotment", "us_stocks": "US stocks", "other": "this question",
}
INTENT_TEAM = {i: t for i, t, _, _ in INTENTS}
INTENT_TEAM["other"] = "Customer Support"


@dataclass
class IntentResult:
    intent: str
    fee_type: str | None
    scheme: str | None
    team: str
    matched: list[str]
    schemes_all: list[str]


def classify(text: str) -> IntentResult:
    t = (text or "").lower()
    schemes = [k for k, pats in SCHEMES.items() if any(re.search(p, t) for p in pats)]
    for intent, team, fee, pats in INTENTS:
        hits = [p for p in pats if re.search(p, t)]
        if hits:
            # A scheme mention + generic "charge" is about mutual-fund fees, not DP/brokerage
            return IntentResult(intent, fee, schemes[0] if len(schemes) == 1 else None, team, hits, schemes)
    return IntentResult("other", None, schemes[0] if len(schemes) == 1 else None, "Customer Support", [], schemes)


def fee_type_of_intent(intent: str) -> str | None:
    for i, _, fee, _ in INTENTS:
        if i == intent:
            return fee
    return None
