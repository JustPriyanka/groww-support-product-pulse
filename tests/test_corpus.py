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
    assert out.status == "not_covered" and "US stocks" in out.note and out.topic == "US stocks"


def _nri_fact(monkeypatch):
    import agents.facts as facts
    sid = next(s.sid for s in get_corpus().sentences.values() if "0.10% with min" in s.text)
    monkeypatch.setattr(facts, "chat_json", lambda *a, **k: {"covered": True, "facts": [
        {"claim": "Equity delivery and intraday brokerage is 0.10% with a minimum of ₹100 per order.", "sentence_ids": [sid]}]})
    monkeypatch.setattr(facts.get_corpus(), "search_sentences", lambda *a, **k: [(sid, 1.0)])
    return facts


def test_audience_section_not_used_for_general_question(monkeypatch):
    # The deployed eval answered a resident's brokerage complaint with the NRI brokerage row.
    facts = _nri_fact(monkeypatch)
    out = facts.run("How much brokerage does Groww charge on a stock order?", "brokerage", "brokerage", None)
    assert out.status == "not_covered"


def test_audience_section_used_when_question_names_it(monkeypatch):
    facts = _nri_fact(monkeypatch)
    out = facts.run("What brokerage do NRI accounts pay on equity delivery?", "brokerage", "brokerage", None)
    assert out.status == "covered"


def test_canonical_citing_nri_row_not_reused_for_general_question(monkeypatch):
    import agents.orchestrator as orch
    from core.intents import classify
    c = get_corpus()
    nri = next(s.sid for s in c.sentences.values() if "0.10% with min" in s.text)
    row = {"scheme_scope": None, "source_hashes": {"groww-pricing": c.sources["groww-pricing"].sha256},
           "bullets": [{"text": "x", "sentence_ids": [nri]}]}
    monkeypatch.setattr(orch.db, "all_", lambda *a, **k: [row])
    q = "How much brokerage does Groww charge on a stock order?"
    assert orch.find_canonical(classify(q), q) is None
    q = "What brokerage do NRI accounts pay on equity?"
    assert orch.find_canonical(classify(q), q) is row


def test_scheme_question_ignores_other_schemes_documents(monkeypatch):
    # Deployed: "exit load on HDFC Mid Cap" was answered with the Nifty 50 Index KIM's 0.25% load.
    import agents.facts as facts
    c = get_corpus()
    other = next(s.sid for s in c.sentences.values() if s.source_id == "hdfc-nifty50-kim" and s.citable and "0.25%" in s.text)
    seen = {}
    def fake_chat(system, user, **k):
        seen["prompt"] = user
        return {"covered": True, "facts": [{"claim": "An exit load of 0.25% applies.", "sentence_ids": [other]}]}
    monkeypatch.setattr(facts, "chat_json", fake_chat)
    out = facts.run("Is there an exit load on HDFC Mid Cap Fund if I redeem after 6 months?", "exit_load", "exit_load", "hdfc_mid_cap")
    assert all(f.source_id != "hdfc-nifty50-kim" for f in out.facts)
    assert other not in seen["prompt"]  # the other fund's sentences are not even offered to the model


def test_mtf_section_not_used_for_brokerage_question(monkeypatch):
    # Deployed run 11: the brokerage explainer listed "Intraday to MTF conversion - 0.1% per order".
    import agents.facts as facts
    sid = next(s.sid for s in get_corpus().sentences.values() if s.section == "Intraday to MTF conversion charges" and s.citable)
    monkeypatch.setattr(facts, "chat_json", lambda *a, **k: {"covered": True, "facts": [
        {"claim": "MTF buy order charges are 0.1% per order of the order value.", "sentence_ids": [sid]}]})
    monkeypatch.setattr(facts.get_corpus(), "search_sentences", lambda *a, **k: [(sid, 1.0)])
    assert facts.run("How much brokerage does Groww charge?", "brokerage", "brokerage", None).status == "not_covered"
    assert facts.run("What does converting intraday to MTF cost?", "mtf_interest", "mtf_interest", None).status == "covered"
