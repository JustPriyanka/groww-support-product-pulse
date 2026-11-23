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
