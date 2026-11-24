"""The weekly pulse must stay within MAX_PULSE_WORDS even when many support questions cross the
signal threshold (the deployed eval produced a 273-word pulse with 11 repeated-question topics)."""
from config import MAX_PULSE_WORDS
from core.llm import LLMUnavailable
from core.policy import word_count
from pipeline import weekly

WINDOW = {"start": "2026-11-17", "end": "2026-11-23"}
TOP = [{"name": n, "count": c, "avg_rating": 3.0, "description": "d", "review_ids": ["GP-aaaaaaaaaa", "GP-bbbbbbbbbb"]}
       for n, c in (("Positive User Experience", 72), ("App Performance & Bugs", 20), ("Hidden & High Charges", 17))]
QUOTES = [{"quote": "word " * 30, "review_id": f"GP-q{i}"} for i in range(3)]
CONF = {"statement": "Users are confused about why brokerage fees are charged and how they are calculated for F&O.",
        "count": 4, "window": {"start": "2026-10-27", "end": "2026-11-23"}}
SIGNALS = [{"intent": f"i{i}", "label": f"some fairly long support topic label {i}", "count": 30 - i,
            "window": WINDOW} for i in range(11)]


def _no_llm(*a, **k):
    raise LLMUnavailable("test")


def test_pulse_fits_with_many_signals(monkeypatch):
    monkeypatch.setattr(weekly, "chat_json", _no_llm)
    md = weekly.compose_pulse(WINDOW, 750, 161, TOP, QUOTES, CONF, SIGNALS)
    assert word_count(md) <= MAX_PULSE_WORDS, word_count(md)
    assert SIGNALS[0]["label"] in md            # the most-asked topic is always shown
    assert all(q["review_id"] in md for q in QUOTES)  # evidence is never trimmed
    assert "more" in md                          # hidden topics are counted, not silently dropped


def test_few_signals_all_shown(monkeypatch):
    monkeypatch.setattr(weekly, "chat_json", _no_llm)
    md = weekly.compose_pulse(WINDOW, 750, 161, TOP, QUOTES, CONF, SIGNALS[:3])
    assert all(s["label"] in md for s in SIGNALS[:3]) and "more" not in md
