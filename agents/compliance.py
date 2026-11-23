"""
Compliance Agent — rules first, LLM second opinion that can only ADD flags.

Input is already redacted; PII types come from the ingress guard (the raw values never
reach this agent).
"""
from __future__ import annotations

import logging

from agents.schemas import ComplianceOutput
from core.llm import LLMUnavailable, chat_json
from core.policy import detect_advice_request, detect_performance_request

log = logging.getLogger("agents.compliance")

SYSTEM = """You are a compliance checker for an Indian investment platform's support desk.
Classify the (already redacted) customer message. Do NOT answer it.
- advice_request: asks whether/what to buy, sell, hold, switch, or which fund/stock is better or good.
- performance_request: asks for returns, past performance, expected gains, NAV growth.
- other_concerns: list any of ["fraud_allegation", "legal_threat", "self_harm", "account_security"] that apply, else [].
Return JSON {"advice_request": bool, "performance_request": bool, "other_concerns": [str]}"""


def run(redacted_text: str, pii_types: list[str], use_llm: bool = True) -> ComplianceOutput:
    advice = detect_advice_request(redacted_text)
    perf = detect_performance_request(redacted_text)
    flags = []
    if pii_types:
        flags.append("PII_REDACTED:" + ",".join(pii_types))
    if advice:
        flags.append("ADVICE_REQUEST")
    if perf:
        flags.append("PERFORMANCE_REQUEST")
    llm_flags, llm_used = [], False
    if use_llm:
        try:
            d = chat_json(SYSTEM, redacted_text, fast=True, purpose="compliance", max_tokens=300)
            llm_used = True
            if d.get("advice_request") and not advice:
                advice = True
                llm_flags.append("ADVICE_REQUEST")
            if d.get("performance_request") and not perf:
                perf = True
                llm_flags.append("PERFORMANCE_REQUEST")
            for c in d.get("other_concerns") or []:
                if c in ("fraud_allegation", "legal_threat", "self_harm", "account_security"):
                    llm_flags.append(c.upper())
        except LLMUnavailable as e:
            log.warning("compliance LLM unavailable (%s); rules only", e)
    flags = flags + [f for f in llm_flags if f not in flags]
    scope = "facts_only"
    if advice or perf:
        scope = "facts_only_no_advice_or_performance"
    return ComplianceOutput(pii_types=pii_types, advice_request=advice, performance_request=perf,
                            flags=flags, llm_flags=llm_flags, llm_used=llm_used, allowed_scope=scope)
