from agents.facts import _with_leads
from config import _clean
from core.corpus import get_corpus


def test_headings_are_context_not_citable():
    c = get_corpus()
    h = c.sentences["groww-help-dp-charges#s3"]  # "What are DP charges ...?"
    assert h.heading and not h.citable
    assert all(c.sentences[sid].citable for sid, _ in c.search_sentences("what are dp charges", k=20))


def test_section_heading_travels_with_sentence():
    c = get_corpus()
    nri = next(s for s in c.sentences.values() if "0.10% with min" in s.text)
    assert nri.section == "NRI brokerage charges"
    assert nri.context_text().startswith("[NRI brokerage charges]")


def test_bullet_citation_carries_its_condition():
    # "- Male investors: ... ₹20.00" is only true "For debit (sale) values of ₹100 or more:"
    sids = _with_leads(["groww-help-dp-charges#s7"])
    assert sids[-1] == "groww-help-dp-charges#s7"
    assert "groww-help-dp-charges#s6" in sids
    assert len(sids) == len(set(sids))


def test_env_values_are_cleaned():
    assert _clean('  "gsk_abc" \n') == "gsk_abc"
    assert _clean("   ") is None
    assert _clean(None) is None


def test_market_scoped_question_needs_scoped_facts(monkeypatch):
    # Q: tax on US-stock dividends. A model "answer" built from Indian statutory charges must be dropped.
    import agents.facts as facts
    from core.corpus import get_corpus
    sid = next(s.sid for s in get_corpus().sentences.values() if s.citable and "STT" in s.text)
    monkeypatch.setattr(facts, "chat_json", lambda *a, **k: {"covered": True, "facts": [{"claim": "STT applies.", "sentence_ids": [sid]}]})
    monkeypatch.setattr(facts.get_corpus(), "search_sentences", lambda *a, **k: [(sid, 1.0)])
    out = facts.run("How is tax deducted on dividends from US stocks?", "statutory_gst", "statutory_charges", None)
    assert out.status == "not_covered" and "US stocks" in out.note
