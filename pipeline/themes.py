"""
Review clustering: LLM proposes <= 5 themes, LLM assigns reviews in batches, CODE validates
(unknown IDs dropped, theme cap enforced, counts computed from assignments, quotes verified).
Fallback: deterministic keyword taxonomy (intent families) if the LLM is unavailable.
"""
from __future__ import annotations

import logging
import random
import re
from collections import Counter, defaultdict

from config import MAX_THEMES
from core.llm import LLMUnavailable, chat_json
from core.pii import contains_pii
from core.reviews import Review

log = logging.getLogger("pipeline.themes")

PROPOSE = """You analyse app-store reviews of Groww (Indian investing app) for a product team.
Propose between 3 and {max_themes} themes that together cover ALL the reviews given (include a theme for general praise if many reviews are positive).
Themes must be specific and product-actionable (e.g. "Charges deducted on sell orders not shown upfront"), not vague.
Return JSON {{"themes": [{{"id": "T1", "name": str (<= 8 words), "description": str (<= 25 words)}}]}}"""

ASSIGN = """Assign each review to exactly one theme id from the list, or "none" if no theme fits.
Themes:
{themes}
Return JSON {{"assignments": {{"<review_id>": "<theme id or none>"}}}} covering every review id given."""

FALLBACK_FAMILIES = {
    "Charges, brokerage & fee transparency": {"brokerage", "dp_charges", "statutory_gst", "hidden_charges", "mtf_interest", "exit_load", "expense_ratio", "stamp_duty_mf"},
    "Withdrawals, payments & redemptions": {"withdrawal", "mf_redemption", "sip_failure", "us_stocks"},
    "Order execution, app speed & F&O": {"order_execution", "fno", "ipo"},
    "Customer support & account/KYC issues": {"customer_support", "kyc_account"},
    "General feedback & praise": {"other"},
}


def _sample(reviews: list[Review], n: int) -> list[Review]:
    rnd = random.Random(42)
    neg = [r for r in reviews if r.rating <= 3]
    pos = [r for r in reviews if r.rating > 3]
    k_neg = min(len(neg), int(n * 0.7))
    return rnd.sample(neg, k_neg) + rnd.sample(pos, min(len(pos), n - k_neg))


def _fmt(r: Review, limit: int = 60) -> str:
    words = r.text.split()
    return f"{r.review_id} (★{r.rating}): {' '.join(words[:limit])}"


def cluster(reviews: list[Review]) -> dict:
    """Returns {themes:[{id,name,description,count,review_ids,avg_rating}], method, unassigned}"""
    if not reviews:
        return {"themes": [], "method": "none", "unassigned": 0}
    try:
        sample = _sample(reviews, 90)
        d = chat_json(PROPOSE.format(max_themes=MAX_THEMES), "\n".join(_fmt(r) for r in sample),
                      fast=True, purpose="themes.propose", max_tokens=1200)
        themes = [t for t in (d.get("themes") or []) if isinstance(t, dict) and t.get("name")][:MAX_THEMES]
        if len(themes) < 2:
            raise LLMUnavailable("too few themes proposed")
        for i, t in enumerate(themes, start=1):
            t["id"] = f"T{i}"
            t["name"] = str(t["name"])[:80]
            t["description"] = str(t.get("description", ""))[:200]
        theme_txt = "\n".join(f"{t['id']}: {t['name']} — {t['description']}" for t in themes)
        valid_ids = {r.review_id for r in reviews}
        valid_t = {t["id"] for t in themes}
        assign: dict[str, str] = {}
        for i in range(0, len(reviews), 40):
            batch = reviews[i:i + 40]
            try:
                a = chat_json(ASSIGN.format(themes=theme_txt), "\n".join(_fmt(r, 45) for r in batch),
                              fast=True, purpose="themes.assign", max_tokens=1600).get("assignments") or {}
            except LLMUnavailable:
                a = {}
            for rid, tid in a.items():
                if rid in valid_ids and str(tid) in valid_t:  # code-side validation
                    assign[rid] = str(tid)
        if len(assign) < 0.5 * len(reviews):
            raise LLMUnavailable(f"only {len(assign)}/{len(reviews)} reviews assigned")
        method = "llm"
    except LLMUnavailable as e:
        log.warning("theme clustering fallback: %s", e)
        themes = [{"id": f"T{i}", "name": n, "description": "keyword taxonomy fallback"} for i, n in enumerate(FALLBACK_FAMILIES, 1)]
        fam = {intent: f"T{i}" for i, (n, ints) in enumerate(FALLBACK_FAMILIES.items(), 1) for intent in ints}
        assign = {r.review_id: fam.get(r.intent, "T5") for r in reviews}
        method = "keyword_fallback"
    by_t: dict[str, list[Review]] = defaultdict(list)
    rmap = {r.review_id: r for r in reviews}
    for rid, tid in assign.items():
        by_t[tid].append(rmap[rid])
    out = []
    for t in themes:
        rs = sorted(by_t.get(t["id"], []), key=lambda r: (r.date, r.review_id), reverse=True)
        if not rs:
            continue
        out.append({**t, "count": len(rs), "review_ids": [r.review_id for r in rs],
                    "avg_rating": round(sum(r.rating for r in rs) / len(rs), 2),
                    "intents": Counter(r.intent for r in rs).most_common(3)})
    out.sort(key=lambda t: t["count"], reverse=True)
    return {"themes": out, "method": method, "unassigned": len(reviews) - len(assign)}


def pick_quote(theme: dict, rmap: dict[str, Review], used: set[str]) -> dict | None:
    """A real, verbatim, PII-free quote (<= 35 words, whole sentences) that is ON-TOPIC for the theme."""
    from core.corpus import tokenize
    topic = set(tokenize(theme["name"] + " " + theme.get("description", ""), expand=True))
    cands = [rmap[i] for i in theme["review_ids"] if i in rmap and i not in used]
    negative = theme["avg_rating"] < 3.5

    def score(r: Review) -> tuple:
        overlap = len(topic & set(tokenize(r.text)))
        return (-overlap, not (10 <= r.words <= 70), r.rating if negative else -r.rating, -r.words)

    for r in sorted(cands, key=score):
        if "_REDACTED]" in r.text or contains_pii(r.text):
            continue
        sents = re.split(r"(?<=[.!?])\s+", " ".join(r.text.split()))
        quote = ""
        for snt in sents:
            cand = (quote + " " + snt).strip()
            if len(cand.split()) > 35:
                break
            quote = cand
        if not quote or len(quote.split()) < 6:
            continue  # only whole sentences; skip reviews whose first sentence is too long
        assert quote in " ".join(r.text.split())  # verbatim
        return {"review_id": r.review_id, "theme": theme["name"], "quote": quote, "rating": r.rating,
                "date": r.date.isoformat(), "source_url": r.source_url, "verbatim": True}
    return None
