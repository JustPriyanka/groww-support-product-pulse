from agents.reviewer import review_reply
from agents.schemas import Citation
from core.corpus import get_corpus

def _cit():
    c = get_corpus()
    sid = next(s for s in c.sentences if s.startswith("groww-help-dp-per-order") and "per sell order" in c.sentences[s].text)
    src = c.sources["groww-help-dp-per-order"]
    return Citation(n=1, source_id=src.id, url=src.url, title=src.title, publisher=src.publisher,
                    sentence_ids=[sid], quotes=[c.sentences[sid].text], last_checked=src.fetched_at)

def codes(r): return {f.code for f in r.flags}

def test_pass():
    assert review_reply("DP charges are applied per sell order, not per stock [1].", [_cit()], "2026-11-23").passed

def test_uncited_claim():
    r = review_reply("DP charges are per sell order [1]. Groww is the cheapest broker.", [_cit()], "2026-11-23")
    assert "UNCITED_CLAIM" in codes(r)

def test_ungrounded_number():
    assert "UNGROUNDED_NUMBER" in codes(review_reply("DP charges are ₹25 per sell order [1].", [_cit()], "2026-11-23"))

def test_bad_citation_target():
    c = _cit(); c.sentence_ids = ["groww-help-dp-per-order#s9999"]
    assert "UNCITED_CLAIM" in codes(review_reply("DP charges are per sell order [1].", [c], "2026-11-23"))

def test_advice_performance_pii_length_lastchecked():
    r = review_reply("You should buy HDFC Mid Cap [1]. It delivered 24% CAGR [1]. Call 9876543210 [1]. Four [1].", [_cit()], None)
    assert {"INVESTMENT_ADVICE", "PERFORMANCE_FIGURE", "PII_PRESENT", "TOO_LONG", "MISSING_LAST_CHECKED"} <= codes(r)

def test_templates_need_no_citation():
    from core.policy import NO_ADVICE_SENTENCE, not_covered_sentence
    assert review_reply(f"{NO_ADVICE_SENTENCE} {not_covered_sentence('F&O margin and trading rules')}", [], "2026-11-23").passed
