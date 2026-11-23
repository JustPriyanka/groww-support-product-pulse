"""
Orchestrator — combines Facts / Pattern / Compliance into:
  * a facts-only customer reply (<= 3 sentences, [n] citations, Last checked)
  * an internal routing note (team, priority, reasons, disagreements)

Policy sentences (no advice / no performance / not covered / PII notice) are fixed
code templates, never LLM-written. The LLM only phrases sentences from verified facts.
"""
from __future__ import annotations

import json
import logging
import re

from agents.schemas import Citation, ComplianceOutput, FactsOutput, PatternOutput, Routing
from config import MAX_REPLY_SENTENCES
from core import db
from core.corpus import get_corpus, tokenize
from core.intents import INTENT_TEAM, IntentResult
from core.llm import LLMUnavailable, chat_json
from core.policy import (NO_ADVICE_SENTENCE, NO_PERFORMANCE_SENTENCE, PII_NOTICE_SENTENCE, not_covered_sentence,
                         split_sentences)

log = logging.getLogger("agents.orchestrator")

SYSTEM = """You write customer-support reply sentences for Groww using ONLY the numbered facts provided.
Rules (strict):
- Write at most {k} sentence(s). Each sentence must end with citation markers for the facts it uses, e.g. "... [1]." or "... [1][2]."
- Use only facts given; keep every number, %, ₹ amount exactly as in the fact. No other numbers.
- If the facts contain specific charges or amounts, state them (with their conditions) instead of saying
  the amount "varies"; a customer asking about a deduction needs the actual figures.
- Neutral, factual tone. No recommendations, no opinions about whether to buy/sell/hold, no returns or performance.
- Do not mention internal teams, priorities, or review data. No greetings or sign-offs.
{extra}
Return JSON {{"sentences": [{{"text": str, "facts": [int]}}]}} where facts are fact numbers used."""


# --------------------------------------------------------------------------- canonical reuse
def find_canonical(intent: IntentResult) -> dict | None:
    """Reuse only if fee type matches, scheme scope matches, and sources are unchanged."""
    if not intent.fee_type:
        return None
    corpus = get_corpus()
    rows = db.all_("SELECT * FROM canonical_explainers WHERE active=1 AND fee_type=? ORDER BY id DESC", intent.fee_type)
    for row in rows:
        scope = row.get("scheme_scope")
        if scope and scope != intent.scheme:
            continue
        if not scope and intent.scheme and intent.fee_type in ("exit_load", "expense_ratio"):
            continue  # scheme-specific question needs a scheme-specific explainer
        hashes = row.get("source_hashes") or {}
        if any(sid not in corpus.sources or corpus.sources[sid].sha256 != h for sid, h in hashes.items()):
            continue  # source coverage changed since approval
        return row
    return None


def _citations_from_facts(facts: FactsOutput) -> tuple[list[Citation], dict[int, int]]:
    """Group facts by source -> citation numbers. Returns (citations, fact_index -> n)."""
    cits: list[Citation] = []
    by_src: dict[str, Citation] = {}
    fmap: dict[int, int] = {}
    for i, f in enumerate(facts.facts, start=1):
        c = by_src.get(f.source_id)
        if not c:
            c = Citation(n=len(cits) + 1, source_id=f.source_id, url=f.url, title=f.title, publisher=f.publisher,
                         sentence_ids=[], quotes=[], last_checked=f.last_checked)
            by_src[f.source_id] = c
            cits.append(c)
        for sid, q in zip(f.sentence_ids, f.quotes):
            if sid not in c.sentence_ids:
                c.sentence_ids.append(sid)
                c.quotes.append(q)
        fmap[i] = c.n
    return cits, fmap


def _templates(facts: FactsOutput, comp: ComplianceOutput) -> list[str]:
    t = []
    if comp.advice_request:
        t.append(NO_ADVICE_SENTENCE)
    if comp.performance_request:
        t.append(NO_PERFORMANCE_SENTENCE)
    if facts.status == "not_covered":
        t.append(not_covered_sentence(facts.topic))
    return t[:MAX_REPLY_SENTENCES]


def _with_pii_notice(parts: list[str], comp: ComplianceOutput) -> list[str]:
    """PII notice goes last and only if it fits the sentence limit (routing note always records it)."""
    if comp.pii_types and len(parts) < MAX_REPLY_SENTENCES:
        return parts + [PII_NOTICE_SENTENCE]
    return parts


def compose_reply(question: str, facts: FactsOutput, comp: ComplianceOutput, *, feedback: str = "",
                  fault: str | None = None) -> tuple[str, list[Citation], str]:
    """Returns (reply_text, citations, mode)."""
    templates = _templates(facts, comp)
    budget = MAX_REPLY_SENTENCES - len(templates)
    if facts.status != "covered" or budget <= 0:
        return " ".join(_with_pii_notice(templates, comp)), [], "template"
    cits, fmap = _citations_from_facts(facts)
    fact_list = "\n".join(f"{i}. {f.claim}" for i, f in enumerate(facts.facts, start=1))
    extra = ""
    if comp.advice_request or comp.performance_request:
        extra = "- The customer asked for advice/performance; answer ONLY the factual part using the facts."
    if feedback:
        extra += f"\n- Reviewer/editor feedback to address: {feedback}"
    mode = "llm"
    sentences: list[tuple[str, list[int]]] = []
    try:
        d = chat_json(SYSTEM.format(k=budget, extra=extra), f"Question: {question}\n\nFacts:\n{fact_list}",
                      purpose="orchestrator", max_tokens=800)
        for s in (d.get("sentences") or [])[:budget]:
            if isinstance(s, dict) and s.get("text"):
                fs = [int(x) for x in s.get("facts") or [] if str(x).isdigit() and int(x) in fmap]
                sentences.append((str(s["text"]).strip(), fs))
    except LLMUnavailable as e:
        log.warning("orchestrator LLM unavailable (%s); deterministic composition", e)
        mode = "deterministic"
    if not sentences:
        mode = "deterministic"
        sentences = [(f.claim, [i]) for i, f in enumerate(facts.facts[:budget], start=1)]
    parts = []
    for text, fs in sentences:
        text = re.sub(r"\s*(\[\d+\])+\s*(?=[.!?]?$)", "", text).strip()  # drop model markers; we re-add canonical ones
        text = re.sub(r"\s*\[\d+\]", "", text)
        text = text.rstrip(".!? ")
        markers = "".join(f"[{n}]" for n in sorted({fmap[i] for i in fs})) if fs else ""
        parts.append(f"{text} {markers}.".replace(" .", ".") if markers else f"{text}.")
    if fault in ("uncited", "uncited_twice"):
        parts.append("Groww's charges are the lowest in the industry.")  # eval-only fault injection
    reply = " ".join(_with_pii_notice(templates + parts, comp))
    used = {int(n) for n in re.findall(r"\[(\d+)\]", reply)}
    cits = [c for c in cits if c.n in used]
    return reply, cits, mode


def compose_from_canonical(question: str, canon: dict, comp: ComplianceOutput) -> tuple[str, list[Citation]]:
    """Reuse the APPROVED explainer verbatim (most relevant bullets within the sentence budget)."""
    templates = _templates(FactsOutput(status="covered", searched={}, topic=""), comp)
    budget = MAX_REPLY_SENTENCES - len(templates)
    bullets = canon["bullets"]
    cits = [Citation(**c) for c in canon["citations"]]
    q = set(tokenize(question, expand=True))
    ranked = sorted(range(len(bullets)), key=lambda i: -len(q & set(tokenize(bullets[i]["text"]))))
    chosen = sorted(ranked[:max(budget, 0)])
    parts = []
    for i in chosen:
        b = bullets[i]
        text = b["text"].rstrip(".!? ")
        parts.append(f"{text} {''.join(f'[{n}]' for n in b['cites'])}.")
    reply = " ".join(_with_pii_notice(templates + parts, comp))
    used = {int(n) for n in re.findall(r"\[(\d+)\]", reply)}
    return reply, [c for c in cits if c.n in used]


# --------------------------------------------------------------------------- routing
def route(intent: IntentResult, facts: FactsOutput, pattern: PatternOutput, comp: ComplianceOutput,
          canonical_used: bool) -> Routing:
    team = INTENT_TEAM.get(intent.intent, "Customer Support")
    if team == "—":
        team = "Customer Support"
    also, reasons, dis = [], [], []
    if comp.pii_types:
        also.append("Trust & Safety")
        reasons.append(f"customer shared personal data ({', '.join(comp.pii_types)}); redacted before processing")
    if any(f in comp.flags for f in ("FRAUD_ALLEGATION", "LEGAL_THREAT")):
        also.append("Trust & Safety")
        reasons.append("fraud/legal language detected")
    if pattern.classification == "rising":
        prio = "P1"
    elif pattern.classification == "recurring":
        prio = "P2"
    else:
        prio = "P3"
    if comp.pii_types and prio == "P3":
        prio = "P2"
    reasons.append(f"pattern={pattern.classification}: {pattern.rationale}")
    reasons.append(f"facts={facts.status}" + (" (approved canonical explainer reused)" if canonical_used else ""))
    if facts.status == "covered" and pattern.classification in ("rising", "recurring"):
        also.append("Product")
        dis.append(f"Facts: answerable from official sources, but Pattern: {pattern.classification} issue "
                   f"({pattern.question_count_7d} questions in 7 days, {pattern.recent_review_count} reviews in the last 4 weeks "
                   f"of {pattern.review_window['start']}–{pattern.review_window['end']}). Reply AND escalate to Product.")
    if facts.status == "not_covered" and pattern.classification != "isolated":
        dis.append("Facts: not covered by official corpus, while Pattern shows a repeated issue — corpus gap; ask the owning team for an official answer.")
    if (comp.advice_request or comp.performance_request) and facts.status == "covered":
        dis.append("Compliance: advice/performance requested — reply limited to the factual part.")
    also = list(dict.fromkeys(a for a in also if a != team))
    note = f"Route to {team}" + (f" (+{', '.join(also)})" if also else "") + f", {prio}. " + " ".join(dis[:1])
    return Routing(team=team, also_notify=also, priority=prio, reasons=reasons, disagreements=dis, note=note.strip())


def last_checked_for(cits: list[Citation], facts: FactsOutput) -> str:
    if cits:
        return max(c.last_checked for c in cits)
    corpus = get_corpus()
    srcs = facts.searched.get("sources_considered") or list(corpus.sources)
    return max(corpus.sources[s].fetched_at for s in srcs if s in corpus.sources)


def snapshot(facts: FactsOutput, pattern: PatternOutput, comp: ComplianceOutput) -> dict:
    return json.loads(json.dumps({"facts": facts.model_dump(), "pattern": pattern.model_dump(), "compliance": comp.model_dump()}))
