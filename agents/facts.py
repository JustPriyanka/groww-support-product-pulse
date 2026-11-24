"""
Facts Agent — official corpus only.

1. BM25 retrieval (scheme-aware) over sentence-ID'd chunks.
2. LLM may only SELECT sentence IDs from the retrieved candidates and paraphrase them.
3. Code keeps a fact only if every cited ID exists in the candidates and every number in the
   claim appears in the cited sentences. No surviving fact -> "not_covered" + what was searched.
"""
from __future__ import annotations

import logging
import re

from agents.schemas import Fact, FactsOutput
from core.corpus import get_corpus, tokenize
from core.intents import FEE_TYPE_LABELS, INTENT_LABELS, SCHEME_NAMES
from core.llm import LLMUnavailable, chat_json
from core.policy import find_advice, find_performance, numbers_in

log = logging.getLogger("agents.facts")

SYSTEM = """You are the Facts Agent for Groww customer support.
You receive a customer question and numbered candidate sentences from OFFICIAL sources (AMC, SEBI, AMFI, Groww).
Rules:
- Use ONLY the candidate sentences. Never use general knowledge. If they do not answer the question, return covered=false.
- Each fact must cite the sentence_ids it is based on, exactly as given.
- Each claim is ONE plain sentence of at most 30 words that a customer can read. Never copy table
  rows, form templates, or long legal clauses; if the relevant sentence is a table or template, leave it out.
- Paraphrase minimally; keep every number, %, and ₹ amount exactly as written in the cited sentence.
- Never include investment advice, recommendations, or return/performance figures, even if a sentence contains them.
- A [bracketed] prefix is the section heading the sentence sits under. Respect it: a sentence under
  "NRI brokerage charges" applies only to NRIs, so do not state it as a general rule.
- A (parenthesised) prefix is the list heading a bullet belongs to, e.g. "(For debit values below ₹100:)".
  Keep that condition in the claim; never state a bullet without it.
- Prefer facts that directly answer the question. For questions about a charge, explain why it applies
  AND state the exact amounts with their conditions; at most 4 facts.
Return JSON: {"covered": bool, "facts": [{"claim": str, "sentence_ids": [str]}], "missing": str}"""

INTENT_QUERY_HINTS = {
    "dp_charges": "DP charges depository participant charges debited when selling shares per scrip",
    "brokerage": "brokerage charges per executed order equity delivery intraday",
    "statutory_gst": "statutory charges GST STT stamp duty exchange transaction charges SEBI fee",
    "hidden_charges": "charges brokerage DP charges statutory charges GST STT stamp duty contract note",
    "mtf_interest": "MTF margin trading facility interest charges per day",
    "exit_load": "exit load redeemed switched out within days of allotment",
    "expense_ratio": "total expense ratio TER direct plan regular plan",
    "stamp_duty_mf": "stamp duty 0.005% mutual fund purchase units allotment",
    "sip_failure": "SIP instalment failed mandate bank bounce",
    "mf_redemption": "redemption proceeds credited working days",
    "withdrawal": "withdrawal balance bank account credited",
    "kyc_account": "KYC account",
}


# Questions scoped to a market the official corpus does not describe must not be answered
# with facts about a different market (e.g. Indian STT/stamp duty for "tax on US-stock
# dividends"). A fact survives only if its cited text or section mentions the scope.
SCOPES = {
    "US stocks": re.compile(r"\b(?:us|u\.s\.|american)\s+(?:stocks?|shares?|markets?|equit\w*)|\bnasdaq\b|\bnyse\b", re.I),
}


# Pricing rows that apply only to a specific audience, product or event. Citing them for a general
# question states the wrong figure (the NRI row "0.10% with min ₹100" was given to residents).
# A sentence under such a section is usable only when the question names the same audience.
AUDIENCE_SECTIONS = {
    "NRI": re.compile(r"\bNRIs?\b|non[- ]resident", re.I),
    "buyback": re.compile(r"\bbuy[- ]?backs?\b", re.I),
    "OFS": re.compile(r"\bOFS\b|offer for sale", re.I),
    "MTF": re.compile(r"\bMTF\b|margin trading", re.I),
}


MAX_FACT_WORDS = 40


def _audience_mismatch(question: str, sids: list[str]) -> bool:
    corpus = get_corpus()
    return any(rx.search(corpus.sentences[s].section) and not rx.search(question)
               for s in sids for rx in AUDIENCE_SECTIONS.values())


def _scope_of(question: str) -> tuple[str, re.Pattern] | None:
    return next(((name, rx) for name, rx in SCOPES.items() if rx.search(question)), None)


def _with_leads(sids: list[str]) -> list[str]:
    """A cited bullet ("- Male investors: ₹20.00") is only correct together with the line it
    hangs off ("For debit (sale) values of ₹100 or more:"), so cite that line too."""
    corpus = get_corpus()
    out: list[str] = []
    for sid in sids:
        chain, cur = [], corpus.sentences[sid].lead_sid
        while cur and cur not in out and cur not in chain and len(chain) < 3:
            chain.insert(0, cur)
            cur = corpus.sentences[cur].lead_sid
        out += [c for c in chain if c not in out]
        if sid not in out:
            out.append(sid)
    return out


def _scheme_sources(scheme: str | None) -> set[str]:
    if not scheme:
        return set()
    c = get_corpus()
    return {s.id for s in c.sources.values() if scheme in s.topics}


def _other_scheme_sources(scheme: str | None) -> set[str]:
    if not scheme:
        return set()
    c = get_corpus()
    return {s.id for s in c.sources.values() if any(t in SCHEME_NAMES and t != scheme for t in s.topics)}


def _topic(question: str, intent: str, fee_type: str | None, scheme: str | None) -> str:
    base = FEE_TYPE_LABELS.get(fee_type or "") or INTENT_LABELS.get(intent, "this question")
    return f"{base} for {SCHEME_NAMES[scheme]}" if scheme else base


def run(question: str, intent: str, fee_type: str | None, scheme: str | None,
        extra_query: str = "", source_restrict: set[str] | None = None) -> FactsOutput:
    corpus = get_corpus()
    query = " ".join(filter(None, [question, INTENT_QUERY_HINTS.get(intent, ""), SCHEME_NAMES.get(scheme or "", ""), extra_query]))
    scheme_src = _scheme_sources(scheme)
    hits = []
    if scheme_src:
        hits += corpus.search(query, k=4, source_filter=scheme_src)
    hits += corpus.search(query, k=6, source_filter=source_restrict)
    seen, chunks = set(), []
    for c, s in hits:
        if c.cid not in seen:
            seen.add(c.cid)
            chunks.append((c, s))
    cand_ids: list[str] = []
    # sentence-level hits first (precise facts buried in long PDFs), then chunk context
    sent_hits = (corpus.search_sentences(query, k=6, source_filter=scheme_src) if scheme_src else []) + \
        corpus.search_sentences(query, k=10, source_filter=source_restrict)
    for sid, _ in sent_hits:
        if sid not in cand_ids:
            cand_ids.append(sid)
    for c, _ in chunks:
        for sid in c.sentence_ids:
            if sid not in cand_ids and corpus.sentences[sid].citable:  # headings: context only
                cand_ids.append(sid)
    # a question about one fund must not be answered from another fund's KIM
    other_src = _other_scheme_sources(scheme)
    cand_ids = [sid for sid in cand_ids if corpus.sentences[sid].source_id not in other_src][:28]
    searched = {
        "query_terms": sorted(set(tokenize(query)))[:25],
        "sources_considered": sorted({c.source_id for c, _ in chunks} | {corpus.sentences[s].source_id for s, _ in sent_hits}),
        "top_chunks": [{"chunk": c.cid, "score": round(s, 2)} for c, s in chunks[:6]],
        "scheme_filter": SCHEME_NAMES.get(scheme or ""),
        "corpus_size": len(corpus.sources),
    }
    topic = _topic(question, intent, fee_type, scheme)
    if not cand_ids:
        return FactsOutput(status="not_covered", searched=searched, topic=topic, note="no retrieval hits")

    def _line(sid: str) -> str:
        st = corpus.sentences[sid]
        lead = f"({corpus.sentences[st.lead_sid].text}) " if st.lead_sid else ""
        return f"[{sid}] ({corpus.sources[st.source_id].publisher}) {lead}{st.context_text()}"[:420]
    listing = "\n".join(_line(sid) for sid in cand_ids)
    mode = "llm"
    try:
        data = chat_json(SYSTEM, f"Customer question: {question}\n\nCandidate sentences:\n{listing}", purpose="facts", max_tokens=1500)
        raw_facts = data.get("facts") or [] if data.get("covered", True) else []
    except LLMUnavailable as e:
        log.warning("facts agent LLM unavailable (%s); extractive fallback", e)
        mode = "extractive"
        q = set(tokenize(query, expand=True))
        scored = sorted(cand_ids, key=lambda sid: -len(q & set(tokenize(corpus.sentences[sid].text))))
        raw_facts = [{"claim": corpus.sentences[sid].text, "sentence_ids": [sid]} for sid in scored[:2]
                     if len(q & set(tokenize(corpus.sentences[sid].text))) >= 3]

    facts: list[Fact] = []
    cand = set(cand_ids)
    scope = _scope_of(question)
    for f in raw_facts[:4]:
        if not isinstance(f, dict):
            continue
        sids = [s for s in (f.get("sentence_ids") or []) if isinstance(s, str)]
        claim = str(f.get("claim") or "").strip()
        if not claim or not sids or any(s not in cand for s in sids):
            continue  # invented / out-of-candidate citation -> dropped
        src_ids = {corpus.sentences[s].source_id for s in sids}
        if len(src_ids) != 1:
            # keep the claim tied to one source for a clean citation; split by first source
            first = corpus.sentences[sids[0]].source_id
            sids = [s for s in sids if corpus.sentences[s].source_id == first]
        sids = _with_leads(sids)
        quotes = [corpus.sentences[s].text for s in sids]
        if not numbers_in(claim) <= numbers_in(" ".join(quotes)):
            continue  # number not in cited text -> dropped
        if len(claim.split()) > MAX_FACT_WORDS:
            continue  # verbatim dump of a table / legal clause, not a readable fact
        if find_advice(claim) or find_performance(claim):
            continue
        if _audience_mismatch(question, sids):
            continue  # NRI / buyback / OFS row cited for a question that is not about it
        if scope and not any(scope[1].search(corpus.sentences[s].context_text()) for s in sids):
            continue  # fact is about a different market than the question
        src = corpus.sources[corpus.sentences[sids[0]].source_id]
        claim = re.sub(r"\s*\[\d+\]", "", claim)
        facts.append(Fact(claim=claim, sentence_ids=sids, source_id=src.id, url=src.url, title=src.title,
                          publisher=src.publisher, quotes=quotes, last_checked=src.fetched_at))
    if not facts:
        note = (f"official sources do not cover {scope[0]}" if scope and raw_facts
                else "retrieved sources did not contain a verifiable answer")
        if scope:
            topic = scope[0]  # name the market asked about, not the keyword-guessed fee type
        return FactsOutput(status="not_covered", searched=searched, topic=topic, mode=mode, note=note)
    return FactsOutput(status="covered", facts=facts, searched=searched, topic=topic, mode=mode)
