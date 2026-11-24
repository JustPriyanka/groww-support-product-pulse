"""
Reviewer — deterministic hard-failure checks. Runs on every reply draft (generated,
corrected, canonical, human-edited), on the weekly pulse, and on the fee explainer.
"""
from __future__ import annotations

import re

from agents.schemas import Citation, ReviewFlag, ReviewResult
from config import MAX_EXPLAINER_BULLETS, MAX_PULSE_WORDS, MAX_REPLY_SENTENCES
from core.corpus import get_corpus
from core.pii import contains_pii
from core.policy import (CITE_RE, find_advice, find_performance, is_template_sentence, numbers_in,
                         split_sentences, word_count)

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _check_citations(citations: list[Citation]) -> list[ReviewFlag]:
    corpus = get_corpus()
    flags = []
    for c in citations:
        src = corpus.sources.get(c.source_id)
        if not src or src.url != c.url:
            flags.append(ReviewFlag(code="UNCITED_CLAIM", detail=f"citation [{c.n}] does not resolve to a corpus source"))
            continue
        for sid in c.sentence_ids:
            s = corpus.resolve(sid)
            if not s or s.source_id != c.source_id:
                flags.append(ReviewFlag(code="UNCITED_CLAIM", detail=f"citation [{c.n}] sentence {sid} not in corpus"))
    return flags


MAX_SENTENCE_WORDS = 40  # longer "sentences" in practice are pasted tables / legal clauses


def review_reply(reply: str, citations: list[Citation], last_checked: str | None) -> ReviewResult:
    flags: list[ReviewFlag] = []
    sentences = split_sentences(reply)
    by_n = {c.n: c for c in citations}
    corpus = get_corpus()
    if not sentences:
        flags.append(ReviewFlag(code="EMPTY", detail="reply is empty"))
    if len(sentences) > MAX_REPLY_SENTENCES:
        flags.append(ReviewFlag(code="TOO_LONG", detail=f"{len(sentences)} sentences > {MAX_REPLY_SENTENCES}"))
    flags += _check_citations(citations)
    for s in sentences:
        if is_template_sentence(s):
            continue
        if len(CITE_RE.sub("", s).split()) > MAX_SENTENCE_WORDS:
            flags.append(ReviewFlag(code="TOO_LONG", detail=f"sentence over {MAX_SENTENCE_WORDS} words", sentence=s[:120]))
        ns = [int(x) for x in CITE_RE.findall(s)]
        if not ns:
            flags.append(ReviewFlag(code="UNCITED_CLAIM", detail="sentence has no citation", sentence=s))
            continue
        bad = [n for n in ns if n not in by_n]
        if bad:
            flags.append(ReviewFlag(code="UNCITED_CLAIM", detail=f"citation(s) {bad} not in source list", sentence=s))
            continue
        cited_text = " ".join(corpus.resolve(sid).text for n in ns for sid in by_n[n].sentence_ids if corpus.resolve(sid))
        missing = numbers_in(CITE_RE.sub("", s)) - numbers_in(cited_text)
        if missing:
            flags.append(ReviewFlag(code="UNGROUNDED_NUMBER", detail=f"numbers {sorted(missing)} not in cited source", sentence=s))
    adv = find_advice(reply)
    if adv:
        flags.append(ReviewFlag(code="INVESTMENT_ADVICE", detail=f"advice phrasing: {adv[0]!r}"))
    perf = find_performance(reply)
    if perf:
        flags.append(ReviewFlag(code="PERFORMANCE_FIGURE", detail=f"performance phrasing: {perf[0]!r}"))
    pii = contains_pii(reply)
    if pii:
        flags.append(ReviewFlag(code="PII_PRESENT", detail=f"PII types: {pii}"))
    if not last_checked or not _DATE.match(last_checked):
        flags.append(ReviewFlag(code="MISSING_LAST_CHECKED", detail="no valid 'Last checked' date"))
    return ReviewResult(passed=not flags, flags=flags, checks={
        "sentences": len(sentences), "citations": len(citations),
        "template_sentences": sum(1 for s in sentences if is_template_sentence(s))})


def review_explainer(bullets: list[dict], citations: list[Citation], last_checked: str | None) -> ReviewResult:
    """bullets: [{text, cites:[n]}]"""
    flags: list[ReviewFlag] = []
    if not bullets:
        flags.append(ReviewFlag(code="EMPTY", detail="no bullets"))
    if len(bullets) > MAX_EXPLAINER_BULLETS:
        flags.append(ReviewFlag(code="TOO_LONG", detail=f"{len(bullets)} bullets > {MAX_EXPLAINER_BULLETS}"))
    flags += _check_citations(citations)
    urls = {c.url for c in citations}
    if len(urls) < 2:
        flags.append(ReviewFlag(code="MISSING_SOURCES", detail=f"{len(urls)} official link(s); 2 required"))
    corpus = get_corpus()
    by_n = {c.n: c for c in citations}
    for b in bullets:
        text = b["text"]
        ns = b.get("cites") or []
        if not ns or any(n not in by_n for n in ns):
            flags.append(ReviewFlag(code="UNCITED_CLAIM", detail="bullet lacks a valid citation", sentence=text))
            continue
        cited = " ".join(corpus.resolve(sid).text for n in ns for sid in by_n[n].sentence_ids if corpus.resolve(sid))
        missing = numbers_in(text) - numbers_in(cited)
        if missing:
            flags.append(ReviewFlag(code="UNGROUNDED_NUMBER", detail=f"numbers {sorted(missing)} not in cited source", sentence=text))
    all_text = " ".join(b["text"] for b in bullets)
    if find_advice(all_text):
        flags.append(ReviewFlag(code="INVESTMENT_ADVICE", detail=find_advice(all_text)[0]))
    if find_performance(all_text):
        flags.append(ReviewFlag(code="PERFORMANCE_FIGURE", detail=find_performance(all_text)[0]))
    if contains_pii(all_text):
        flags.append(ReviewFlag(code="PII_PRESENT", detail=str(contains_pii(all_text))))
    if not last_checked or not _DATE.match(last_checked):
        flags.append(ReviewFlag(code="MISSING_LAST_CHECKED", detail="no valid 'Last checked' date"))
    return ReviewResult(passed=not flags, flags=flags, checks={"bullets": len(bullets), "official_links": len(urls)})


def review_pulse(markdown: str, themes: list[dict], quotes: list[dict], window: dict, valid_review_ids: set[str]) -> ReviewResult:
    flags: list[ReviewFlag] = []
    wc = word_count(markdown)
    if wc > MAX_PULSE_WORDS:
        flags.append(ReviewFlag(code="TOO_LONG", detail=f"{wc} words > {MAX_PULSE_WORDS}"))
    for t in themes:
        if not t.get("review_ids"):
            flags.append(ReviewFlag(code="UNTRACEABLE_THEME", detail=f"theme {t.get('name')} has no review IDs"))
        bad = [r for r in t.get("review_ids", []) if r not in valid_review_ids]
        if bad:
            flags.append(ReviewFlag(code="UNTRACEABLE_THEME", detail=f"theme {t.get('name')} cites review IDs outside window: {bad[:3]}"))
    if len(quotes) != 3:
        flags.append(ReviewFlag(code="QUOTES", detail=f"{len(quotes)} quotes; exactly 3 required"))
    for q in quotes:
        if q.get("review_id") not in valid_review_ids:
            flags.append(ReviewFlag(code="UNTRACEABLE_QUOTE", detail=f"quote review {q.get('review_id')} not in window"))
    if contains_pii(markdown):
        flags.append(ReviewFlag(code="PII_PRESENT", detail=str(contains_pii(markdown))))
    if not window.get("start") or not window.get("end"):
        flags.append(ReviewFlag(code="MISSING_WINDOW", detail="no time window"))
    return ReviewResult(passed=not flags, flags=flags, checks={"words": wc, "themes": len(themes), "quotes": len(quotes)})
