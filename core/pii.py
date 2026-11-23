"""
Deterministic PII detection + redaction.

Used at every trust boundary BEFORE persistence, logging, or any agent/LLM call:
  - review ingestion (scripts/collect_reviews.py)
  - incoming questions (typed or voice transcript)
  - LLM outputs (defence in depth: a draft that still contains PII is a hard reviewer failure)

Detection is regex-based on purpose: it is auditable, fast, and does not require sending
the raw text to any third party to find out whether it is sensitive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Order matters: more specific patterns first so that e.g. a card number is not
# reported as an account number, and an email's digits are not reported as a phone.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("UPI_ID", re.compile(r"\b[A-Za-z0-9.\-_]{2,}@(?:ok[a-z]+|ybl|ibl|axl|upi|paytm|apl|yapl|ptyes|ptsbi|ptaxis|pthdfc|icici|sbi|hdfcbank|axisbank|kotak|barodampay|aubank|freecharge|jupiteraxis|slc|waicici|wahdfcbank|waaxis|wasbi)\b", re.I)),
    ("PAN", re.compile(r"\b[A-Z]{3}[ABCFGHLJPTK][A-Z]\d{4}[A-Z]\b", re.I)),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")),
    ("OTP", re.compile(r"\b(?:otp|one[\s-]?time[\s-]?password|verification code|pin)\b[^\d\n]{0,15}(\d{4,8})\b", re.I)),
    ("CARD", re.compile(r"(?<![\w-])(?:\d{4}[\s-]){3}\d{4}(?![\w-])")),
    ("AADHAAR", re.compile(r"(?<![\w₹-])(?<!rs\.)(?<!rs )[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?![\w-])", re.I)),
    ("PHONE", re.compile(r"(?<![\w₹-])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?![\w-])")),
    # Generic long numeric identifiers (bank account, demat/BO id, folio, client code digits).
    ("ACCOUNT_NUMBER", re.compile(r"(?<![\w₹.,-])(?<!rs\.)(?<!rs )(?<!inr )\d{9,18}(?![\w.,-])", re.I)),
    # Explicitly labelled identifiers, any length >= 5
    ("ACCOUNT_NUMBER", re.compile(r"\b(?:a/c|acct|account|folio|demat|dp|client|bo|customer|ucc|order)\b\.?\s*(?:no\b\.?|number|id|code|#)?\s*[:#-]?\s*((?=(?:[A-Z]*\d){3})[A-Z0-9]{5,20}(?:/\d{1,6})?)(?![\w-])", re.I)),
    # Self-identification of a person's name ("my name is X Y")
    ("PERSON_NAME", re.compile(r"\b(?i:my name is|i am|this is|name:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", re.UNICODE)),
    ("PERSON_NAME", re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Shri|Smt|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)")),
]

# Words after "i am" that are not names (avoid redacting "I am Unable", "I am Very")
_NOT_NAMES = {
    "unable", "not", "very", "facing", "getting", "using", "trying", "a", "an", "the", "so",
    "really", "totally", "extremely", "also", "still", "being", "happy", "sad", "disappointed",
    "frustrated", "satisfied", "new", "investing", "writing", "giving", "going", "here", "just",
    "worried", "angry", "glad", "sure", "done", "fed", "loving", "regular", "long", "old", "one",
}

PII_TYPES = ["PAN", "AADHAAR", "ACCOUNT_NUMBER", "OTP", "EMAIL", "PHONE", "CARD", "IFSC", "UPI_ID", "PERSON_NAME"]


@dataclass
class RedactionResult:
    text: str
    found: list[str] = field(default_factory=list)  # PII *types* only, never values

    @property
    def had_pii(self) -> bool:
        return bool(self.found)


def redact(text: str | None) -> RedactionResult:
    """Replace every detected PII span with a typed placeholder like [PAN_REDACTED].

    Returns the redacted text and the list of PII types found. The original values are
    never returned, stored, or logged.
    """
    if not text:
        return RedactionResult(text="" if text is None else text)
    found: list[str] = []
    out = text
    for kind, pat in _PATTERNS:
        def _sub(m: re.Match) -> str:
            # If the pattern has a capture group, redact only the group (keep the label word).
            if m.groups():
                val = m.group(1)
                if kind == "PERSON_NAME" and val.split()[0].lower() in _NOT_NAMES:
                    return m.group(0)
                found.append(kind)
                start, end = m.span(1)
                rel_s, rel_e = start - m.start(), end - m.start()
                whole = m.group(0)
                return whole[:rel_s] + f"[{kind}_REDACTED]" + whole[rel_e:]
            found.append(kind)
            return f"[{kind}_REDACTED]"
        out = pat.sub(_sub, out)
    # stable, de-duplicated order
    seen: list[str] = []
    for k in found:
        if k not in seen:
            seen.append(k)
    return RedactionResult(text=out, found=seen)


def contains_pii(text: str | None) -> list[str]:
    """Return PII types present (empty list = clean). Placeholders are not PII."""
    return redact(text).found


def assert_clean(text: str | None, where: str = "") -> None:
    """Raise if text still contains PII. Used as a last-line guard before writes."""
    kinds = contains_pii(text)
    if kinds:
        raise ValueError(f"PII ({', '.join(kinds)}) would be written to {where or 'storage'}")
