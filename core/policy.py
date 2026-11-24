"""
Deterministic policy rules shared by the Compliance Agent, the Reviewer and the weekly loop.

These are enforced in code; prompts repeat them but are never trusted to obey them.
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------- inputs
_ADVICE_IN = [
    r"\bshould\s+i\s+(?:buy|sell|invest|redeem|switch|hold|continue|stop|exit|start|put|move|withdraw from)\b",
    r"\b(?:is|are)\s+(?:it|this|that|they|hdfc[\w\s-]{0,30}?)\s+(?:a\s+)?(?:good|safe|right|wise|worth|better|best)\b.{0,30}\b(?:invest|buy|fund|option|choice|time)",
    r"\bwhich\s+(?:fund|scheme|stock|share|sip|mutual fund|one)\b.{0,40}\b(?:best|better|good|should|buy|invest|choose|pick)\b",
    r"\b(?:recommend|suggest)\b.{0,30}\b(?:fund|scheme|stock|share|sip|portfolio|invest)",
    r"\bbest\s+(?:fund|mutual fund|scheme|stock|sip|small cap|mid cap|flexi cap|index fund)\b",
    r"\bworth\s+investing\b",
    r"\bgood\s+time\s+to\s+(?:buy|invest|sell|enter|exit)\b",
    r"\b(?:buy|sell|hold)\s+or\s+(?:buy|sell|hold)\b",
    r"\bwhere\s+(?:should|can)\s+i\s+invest\b",
    r"\bhow\s+much\s+should\s+i\s+invest\b",
]
_PERF_IN = [
    r"\breturns?\b.{0,40}\b(?:fund|scheme|year|yr|annual|past|last|give|gave|generated?|expected|percent|%|cagr)\b",
    r"\b(?:fund|scheme|hdfc[\w\s-]{0,30}?)\b.{0,40}\breturns?\b",
    r"\bhow\s+much\s+(?:will|can|would|did)\s+i\s+(?:earn|make|get|gain)\b",
    r"\b(?:cagr|xirr|irr|alpha|sharpe)\b",
    r"\bperformance\b",
    r"\b(?:nav)\s+(?:history|growth|grew|increase|rise|went up)\b",
    r"\b(?:outperform|beat)\w*\s+(?:the\s+)?(?:market|index|nifty|benchmark)\b",
    r"\bprofit\b.{0,20}\b(?:fund|scheme|sip)\b",
]


def detect_advice_request(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in _ADVICE_IN)


def detect_performance_request(text: str) -> bool:
    t = text.lower()
    # "returned my money" / "return my money" is about refunds, not performance
    t = re.sub(r"\breturn(?:ed)?\s+(?:my|the|our)\s+(?:money|funds?|amount)\b", " refund ", t)
    return any(re.search(p, t) for p in _PERF_IN)


# --------------------------------------------------------------------------- outputs
_ADVICE_OUT = [
    r"\b(?:you|investors?|users?|customers?)\s+(?:should|must|may want to|might want to|could)\s+(?:consider\s+)?(?:buy|sell|invest|hold|switch|redeem|exit|stay|continue|stop|start)\b",
    r"\bwe\s+(?:recommend|suggest|advise)\b",
    r"\bi\s+(?:recommend|suggest|advise)\b",
    r"\b(?:is|are)\s+an?\s+(?:good|great|better|safe|ideal|excellent|smart|wise)\s+(?:investment|option|choice|fund|bet)\b",
    r"\bbest\s+(?:fund|option|choice|scheme|investment)\b",
    r"\bconsider\s+investing\b",
    r"\b(?:good|right|ideal)\s+time\s+to\s+(?:buy|invest|sell)\b",
]
_PERF_OUT = [
    r"\d+(?:\.\d+)?\s*%\s*(?:returns?|cagr|annuali[sz]ed returns?|growth|xirr|gains?)",
    r"\b(?:returns?|returned|cagr|xirr|grew|gained|delivered|generated|growth of)\b[^.\n]{0,40}?\d+(?:\.\d+)?\s*%",
    r"\b(?:returns?|cagr)\s+(?:of|was|were|is|are)\b",
    r"\bwill\s+(?:earn|make|grow|double|give)\b",
    r"₹\s?[\d,]+\s+(?:would|will)\s+(?:have\s+)?(?:grown|become)",
    # factsheet / KIM performance tables ("Returns (%) ... Last 3 Years 25.15 ... Since Inception 17.55")
    r"\breturns?\s*\(%\)",
    r"\b(?:last|past)\s+\d+\s+(?:years?|months?)\W{0,3}\s*-?\d+\.\d+",
    r"\bsince\s+inception\W{0,3}\s*-?\d+\.\d+",
    r"\bcompounded\s+annuali[sz]ed\b",
]


def find_advice(text: str) -> list[str]:
    t = text.lower()
    return [m.group(0) for p in _ADVICE_OUT for m in [re.search(p, t)] if m]


def find_performance(text: str) -> list[str]:
    t = text.lower()
    return [m.group(0) for p in _PERF_OUT for m in [re.search(p, t)] if m]


# --------------------------------------------------------------------------- sentences / citations
_ABBR = ["rs.", "no.", "e.g.", "i.e.", "approx.", "ltd.", "pvt.", "vs.", "inc.", "co.", "st.", "mr.", "ms.", "dr.", "etc.", "p.a.", "viz."]
CITE_RE = re.compile(r"\[(\d{1,2})\]")


def split_sentences(text: str) -> list[str]:
    """Sentence splitter that does not break on Rs. / 0.5% / i.e. / decimals."""
    if not text:
        return []
    protected = text
    for i, a in enumerate(_ABBR):
        protected = re.sub(re.escape(a), lambda m, i=i: m.group(0).replace(".", f"§{i}§"), protected, flags=re.I)
    out: list[str] = []
    pos = 0
    for m in re.finditer(r"[.!?](?:\s*\[\d{1,2}\])*(?=\s+[A-Z₹\"'(•●▪]|\s*$)", protected):
        seg = protected[pos:m.end()].strip()
        if seg:
            out.append(seg)
        pos = m.end()
    tail = protected[pos:].strip()
    if tail:
        out.append(tail)

    def restore(s: str) -> str:
        return re.sub(r"§(\d+)§", ".", s)

    return [restore(s) for s in out if restore(s).strip()]


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


_NUM_RE = re.compile(r"(?<![\w\[])(\d[\d,]*(?:\.\d+)?)(?!\])")


_NAMED_NUM = re.compile(r"\b(?:nifty|bse|nse|midcap|smallcap|largecap|sensex|s&p|cnx|nasdaq|nifty\s+midcap|nifty\s+smallcap|bse\s+250\s+smallcap)\s*\d+\b", re.I)


def numbers_in(text: str) -> set[str]:
    """Numbers in text (commas stripped, trailing .0 normalised). Citation markers and
    numbers that are part of index / scheme names ("Nifty 50", "Midcap 150") are excluded."""
    nums = set()
    text = _NAMED_NUM.sub(" ", text or "")
    for m in _NUM_RE.finditer(text):
        n = m.group(1).replace(",", "")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        nums.add(n)
    return nums


# Fixed, code-generated sentences that need no citation (they make no factual claim
# about a product; they describe what the system can / cannot do).
NO_ADVICE_SENTENCE = "We can share official facts but cannot recommend whether to buy, sell or hold any investment."
NO_PERFORMANCE_SENTENCE = "We cannot share return or performance figures; the scheme's official factsheet is the authoritative place to check them."


def not_covered_sentence(topic: str) -> str:
    topic = re.sub(r"[^\w\s&/-]", "", topic).strip() or "this question"
    return f"Our official sources do not cover {topic}, so we have escalated it to the relevant team instead of guessing."


TEMPLATE_PATTERNS = [
    re.escape(NO_ADVICE_SENTENCE),
    re.escape(NO_PERFORMANCE_SENTENCE),
    r"Our official sources do not cover [\w\s&/-]+, so we have escalated it to the relevant team instead of guessing\.",
    r"We have removed personal details you shared; please never share PAN, Aadhaar, account numbers or OTPs in messages\.",
]
PII_NOTICE_SENTENCE = "We have removed personal details you shared; please never share PAN, Aadhaar, account numbers or OTPs in messages."


def is_template_sentence(s: str) -> bool:
    s = s.strip()
    return any(re.fullmatch(p, s) for p in TEMPLATE_PATTERNS)
