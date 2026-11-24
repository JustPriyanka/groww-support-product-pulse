"""
Weekly product loop. Triggered by the scheduler or manually; runs to completion without
human input and ends with PENDING actions (nothing is published here).
"""
from __future__ import annotations

import logging
import re
import threading
import traceback
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from actions import gate
from agents import facts as facts_agent
from agents.reviewer import review_explainer, review_pulse
from agents.schemas import Citation
from config import MAX_EXPLAINER_BULLETS, MAX_PULSE_WORDS, PULSE_WINDOW_DAYS, REFRESH_REVIEWS_ON_RUN, SIGNAL_THRESHOLD
from core import db
from core.corpus import get_corpus
from core.intents import FEE_TYPE_LABELS, INTENT_TEAM
from core.llm import LLMUnavailable, chat_json
from core.policy import find_advice, find_performance, numbers_in, word_count
from core.reviews import all_reviews, in_window, latest_date
from pipeline.themes import cluster, pick_quote

log = logging.getLogger("pipeline.weekly")
_run_lock = threading.Lock()

CONFUSION_WORDS = re.compile(r"hidden|not shown|not showing|not clear|unclear|confus|without (?:my )?(?:consent|inform|know)|didn'?t know|don'?t know|why|extra|deduct|surprise|realis|not (?:dis)?play|unknown|irrelevant|cut|charged", re.I)
FEE_INTENTS = {"brokerage", "dp_charges", "statutory_gst", "hidden_charges", "mtf_interest", "exit_load", "expense_ratio", "stamp_duty_mf"}
# Representative customer question per fee type, used to retrieve the explainer's facts
FEE_QUERIES = {
    "dp_charges": "What are DP charges and why are they deducted when I sell shares? Are they per order?",
    "hidden_charges": "Apart from brokerage what charges are deducted on my trades, DP charges, GST, STT, stamp duty, and where can I see them in the contract note?",
    "brokerage": "What brokerage does Groww charge per order for stocks and what other charges apply?",
    "statutory_charges": "What statutory charges like GST, STT, stamp duty and exchange charges apply to trades?",
    "mtf_interest": "What interest is charged for MTF margin trading facility?",
    "exit_load": "What exit load applies when redeeming HDFC mutual fund units?",
    "expense_ratio": "What is the expense ratio of HDFC mutual fund direct plans?",
    "stamp_duty": "What stamp duty applies when buying mutual fund units?",
}
INTENT_TO_FEE = {"brokerage": "brokerage", "dp_charges": "dp_charges", "statutory_gst": "statutory_charges",
                 "hidden_charges": "hidden_charges", "mtf_interest": "mtf_interest", "exit_load": "exit_load",
                 "expense_ratio": "expense_ratio", "stamp_duty_mf": "stamp_duty"}


def _step(run_id: int, name: str, status: str = "ok", detail: dict | str | None = None) -> None:
    row = db.one("SELECT steps FROM pulse_runs WHERE id=?", run_id)
    steps = row["steps"] if row and isinstance(row["steps"], list) else []
    steps.append({"step": name, "status": status, "at": db.now(), "detail": detail or {}})
    db.update("pulse_runs", run_id, steps=steps)


# --------------------------------------------------------------------------- steps
def refresh_reviews(run_id: int) -> dict:
    """Best effort: pull reviews newer than the snapshot, redact, merge. Never fatal."""
    if not REFRESH_REVIEWS_ON_RUN:
        return {"skipped": "disabled"}
    try:
        from scripts.collect_reviews import fetch_new  # lazy: network dependency
        return fetch_new(since=latest_date() + timedelta(days=1))
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:150]}", "fallback": "committed snapshot"}


def detect_fee_confusion(start: date, end: date) -> dict | None:
    """Most frequent fee/charge confusion in reviews (window, widened to 28 days if thin)."""
    corpus = get_corpus()
    for days in (None, 28):
        s = start if days is None else end - timedelta(days=days - 1)
        rs = [r for r in in_window(s, end) if r.intent in FEE_INTENTS and r.words >= 4]
        confused = [r for r in rs if CONFUSION_WORDS.search(r.text)]
        counts = Counter(INTENT_TO_FEE[r.intent] for r in confused)
        if sum(counts.values()) >= 5:
            break
    if not counts:
        return None
    totals = Counter(INTENT_TO_FEE[r.intent] for r in all_reviews() if r.intent in FEE_INTENTS)
    for fee, n in sorted(counts.items(), key=lambda kv: (-kv[1], -totals[kv[0]])):  # tie-break: 12-week volume
        # must be answerable from the official corpus
        probe = facts_agent.run(FEE_QUERIES[fee], next(i for i, f in INTENT_TO_FEE.items() if f == fee), fee, None)
        if probe.status != "covered":
            continue
        ev = sorted([r for r in confused if INTENT_TO_FEE[r.intent] == fee], key=lambda r: (-r.words, r.date))
        ids = [r.review_id for r in ev]
        statement = None
        try:
            d = chat_json("You summarise what customers are confused about regarding one fee, from app reviews. "
                          "One neutral sentence (<= 30 words), no numbers unless they appear in the reviews, no advice. "
                          'Return JSON {"confusion": str}',
                          "\n".join(f"{r.review_id}: {' '.join(r.text.split()[:60])}" for r in ev[:15]),
                          fast=True, purpose="fee_confusion", max_tokens=300)
            statement = str(d.get("confusion", "")).strip()[:300] or None
        except LLMUnavailable:
            pass
        statement = statement or f"Users report {FEE_TYPE_LABELS.get(fee, fee)} they did not expect or could not see before the deduction."
        return {"fee_type": fee, "label": FEE_TYPE_LABELS.get(fee, fee), "statement": statement, "count": len(ids),
                "review_ids": ids, "window": {"start": s.isoformat(), "end": end.isoformat()},
                "all_fee_counts": dict(counts)}
    return None


def question_signals(now: datetime) -> list[dict]:
    start = now - timedelta(days=7)
    rows = db.all_("SELECT intent, COUNT(*) n FROM questions WHERE created_at>=? AND intent NOT IN ('other','voice_command_blocked') "
                   "GROUP BY intent HAVING n>=? ORDER BY n DESC", start.isoformat(timespec="seconds"), SIGNAL_THRESHOLD)
    return [{"intent": r["intent"], "count": r["n"], "label": FEE_TYPE_LABELS.get(INTENT_TO_FEE.get(r["intent"], ""), r["intent"].replace("_", " ")),
             "team": INTENT_TEAM.get(r["intent"]), "window": {"start": start.date().isoformat(), "end": now.date().isoformat()}}
            for r in rows]


def build_explainer(conf: dict) -> tuple[dict | None, dict]:
    """<= 6 bullets from verified corpus sentences, >= 2 official links, Last checked."""
    corpus = get_corpus()
    fee = conf["fee_type"]
    intent = next(i for i, f in INTENT_TO_FEE.items() if f == fee)
    f1 = facts_agent.run(FEE_QUERIES[fee], intent, fee, None)
    facts = list(f1.facts)
    if len({f.source_id for f in facts}) < 2:  # need a second official source
        f2 = facts_agent.run(FEE_QUERIES[fee], intent, fee, None,
                             source_restrict={s for s in corpus.sources if s not in {f.source_id for f in facts}})
        facts += f2.facts
    if not facts:
        return None, {"error": "no verifiable facts"}
    cits: list[Citation] = []
    by_src: dict[str, Citation] = {}
    for f in facts:
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
    fact_list = "\n".join(f"{i}. [source {by_src[f.source_id].n}] {f.claim}" for i, f in enumerate(facts, 1))
    bullets: list[dict] = []
    feedback = ""
    for attempt in (1, 2):
        try:
            d = chat_json(
                "Write a neutral, customer-facing fee explainer for Groww users from ONLY the numbered facts. "
                f"At most {MAX_EXPLAINER_BULLETS} bullets, each <= 30 words, each ending with the source numbers it uses. "
                "Keep numbers exactly as in the facts. No advice, no opinions, no comparisons with other brokers, no returns. "
                "Address the confusion described. One fact per bullet: never merge or generalise facts beyond what they say. " + feedback +
                ' Return JSON {"title": str, "bullets": [{"text": str, "facts": [int]}]}',
                f"Confusion seen in reviews: {conf['statement']}\n\nFacts:\n{fact_list}",
                purpose="explainer", max_tokens=1200)
            title = str(d.get("title") or f"Understanding {conf['label']}")[:120]
            bullets = []
            for b in (d.get("bullets") or [])[:MAX_EXPLAINER_BULLETS]:
                fs = [int(x) for x in b.get("facts") or [] if str(x).isdigit() and 1 <= int(x) <= len(facts)]
                text = re.sub(r"\s*\[(?:source\s*)?\d+\]", "", str(b.get("text", ""))).strip()
                if not text or not fs:
                    continue
                ns = sorted({by_src[facts[i - 1].source_id].n for i in fs})
                bullets.append({"text": text, "cites": ns, "sentence_ids": [s for i in fs for s in facts[i - 1].sentence_ids]})
        except LLMUnavailable:
            title = f"Understanding {conf['label']}"
            bullets = [{"text": f.claim, "cites": [by_src[f.source_id].n], "sentence_ids": f.sentence_ids} for f in facts[:MAX_EXPLAINER_BULLETS]]
        used = sorted({n for b in bullets for n in b["cites"]})
        used_cits = [c for c in cits if c.n in used]
        lc = max((c.last_checked for c in used_cits), default=None)
        rv = review_explainer(bullets, used_cits, lc)
        if rv.passed:
            break
        feedback = "Previous attempt failed review: " + "; ".join(f"{f.code} {f.detail}" for f in rv.flags) + ". Fix it."
    # renumber citations 1..k
    remap = {c.n: i for i, c in enumerate(used_cits, 1)}
    final_cits = [Citation(**{**c.model_dump(), "n": remap[c.n]}) for c in used_cits]
    for b in bullets:
        b["cites"] = [remap[n] for n in b["cites"]]
    md = f"### {title}\n\n" + "\n".join(f"- {b['text']} " + "".join(f"[{n}]" for n in b["cites"]) for b in bullets)
    md += "\n\nSources: " + " · ".join(f"[{c.n}] {c.publisher} — {c.title} ({c.url})" for c in final_cits)
    md += f"\n\nLast checked: {lc}"
    explainer = {"title": title, "fee_type": fee, "scheme_scope": None, "bullets": bullets,
                 "citations": [c.model_dump() for c in final_cits], "source_ids": [c.source_id for c in final_cits],
                 "last_checked": lc, "markdown": md, "confusion": conf["statement"], "attempts": attempt}
    return explainer, rv.model_dump()


PULSE_MAX_SIGNALS = 5  # signals arrive sorted by count; the rest are summarised as "+N more"


def compose_pulse(window: dict, n_reviews: int, n_sub: int, top: list[dict], quotes: list[dict], conf: dict | None,
                  signals: list[dict]) -> str:
    theme_txt = "\n".join(f"{i}. {t['name']} — {t['count']} reviews, avg ★{t['avg_rating']}: {t['description']}" for i, t in enumerate(top, 1))
    sig_txt = "\n".join(f"- '{s['label']}' asked {s['count']} times ({s['window']['start']} to {s['window']['end']})" for s in signals) or "none"
    ideas, observation = [], ""
    budget_note = ""
    for attempt in (1, 2):
        try:
            d = chat_json(
                "You are a product analyst writing Groww's internal weekly product pulse. Use only the data given. "
                "Return JSON {\"observation\": str (<= 45 words, the single most important insight, cite counts), "
                "\"actions\": [3 strings, each <= 22 words, concrete product action ideas]}" + budget_note,
                f"Window: {window['start']} to {window['end']}\nThemes:\n{theme_txt}\n\nFee confusion: "
                f"{conf['statement'] + ' (' + str(conf['count']) + ' reviews)' if conf else 'none'}\n\nRepeated support questions:\n{sig_txt}",
                purpose="pulse", max_tokens=900)
            observation = str(d.get("observation", "")).strip()
            ideas = [str(a).strip() for a in (d.get("actions") or [])][:3]
        except LLMUnavailable:
            observation = f"'{top[0]['name']}' is the largest theme ({top[0]['count']} reviews)." if top else ""
            ideas = ["Show a full pre-trade charge breakdown before order confirmation.",
                     "Link the contract note from the order screen.", "Add an in-app fee explainer to support replies."]
        md = render_pulse(window, n_reviews, n_sub, top, quotes, conf, signals, observation, ideas)
        if word_count(md) <= MAX_PULSE_WORDS:
            return md
        budget_note = " Be much shorter: observation <= 30 words, actions <= 14 words each."
    # deterministic trims, never of evidence: first list fewer repeated-question topics (the rest
    # are counted as "+N more"), then shorten action text
    shown = PULSE_MAX_SIGNALS
    while word_count(md) > MAX_PULSE_WORDS and shown > 1:
        shown -= 1
        md = render_pulse(window, n_reviews, n_sub, top, quotes, conf, signals, observation, ideas, shown)
    while word_count(md) > MAX_PULSE_WORDS and any(len(a.split()) > 6 for a in ideas):
        ideas = [" ".join(a.split()[:max(6, len(a.split()) - 2)]) for a in ideas]
        md = render_pulse(window, n_reviews, n_sub, top, quotes, conf, signals, observation, ideas, shown)
    return md


def render_pulse(window, n_reviews, n_sub, top, quotes, conf, signals, observation, ideas,
                 max_signals: int = PULSE_MAX_SIGNALS) -> str:
    lines = [f"**Groww Weekly Product Pulse** · {window['start']} → {window['end']} · {n_reviews} Play Store reviews ({n_sub} substantive)", "",
             "**Top themes**"]
    for i, t in enumerate(top, 1):
        ids = ", ".join(t["review_ids"][:2])
        lines.append(f"{i}. {t['name']} — {t['count']} reviews (e.g. {ids})")
    lines += ["", "**Evidence**"]
    for q in quotes:
        lines.append(f"> “{q['quote']}” — {q['review_id']}")
    if conf:
        lines += ["", f"**Fee confusion:** {conf['statement']} ({conf['count']} reviews, {conf['window']['start']} → {conf['window']['end']})"]
    if signals:
        more = len(signals) - max_signals
        lines += ["", "**Repeated questions (≥5/week):** " + "; ".join(f"{s['label']} ×{s['count']}" for s in signals[:max_signals])
                  + (f"; +{more} more" if more > 0 else "")]
    lines += ["", f"**Main observation:** {observation}", "", "**Product action ideas**"]
    lines += [f"{i}. {a}" for i, a in enumerate(ideas, 1)]
    return "\n".join(lines)


# --------------------------------------------------------------------------- run
def run(trigger: str = "manual", end: date | None = None, window_days: int = PULSE_WINDOW_DAYS) -> int:
    if not _run_lock.acquire(blocking=False):
        running = db.one("SELECT id FROM pulse_runs WHERE status='running' ORDER BY id DESC LIMIT 1")
        raise RuntimeError(f"run {running['id'] if running else '?'} already in progress")
    run_id = db.insert("pulse_runs", trigger=trigger, status="running", steps=[], created_at=db.now())
    threading.Thread(target=_execute, args=(run_id, end, window_days), daemon=True).start()
    return run_id


def _execute(run_id: int, end: date | None, window_days: int) -> None:
    try:
        r = refresh_reviews(run_id)
        _step(run_id, "refresh_reviews", "warn" if "error" in r else "ok", r)
        end = end or min(latest_date(), datetime.now(timezone.utc).date())
        start = end - timedelta(days=window_days - 1)
        window = {"start": start.isoformat(), "end": end.isoformat(), "days": window_days}
        db.update("pulse_runs", run_id, window_start=window["start"], window_end=window["end"])
        all_w = in_window(start, end)
        sub = [r for r in all_w if r.words >= 6]
        _step(run_id, "select_window", detail={"reviews": len(all_w), "substantive": len(sub), **window})

        cl = cluster(sub)
        themes = cl["themes"]
        top = themes[:3]
        rmap = {r.review_id: r for r in sub}
        used: set[str] = set()
        quotes = []
        for t in top:
            q = pick_quote(t, rmap, used)
            if q:
                used.add(q["review_id"])
                quotes.append(q)
        _step(run_id, "cluster_themes", detail={"method": cl["method"], "themes": len(themes), "unassigned": cl["unassigned"]})

        conf = detect_fee_confusion(start, end)
        _step(run_id, "fee_confusion", "ok" if conf else "warn", {"fee_type": conf and conf["fee_type"], "count": conf and conf["count"]})

        signals = question_signals(datetime.now(timezone.utc))
        _step(run_id, "question_signals", detail={"signals": len(signals)})

        md = compose_pulse(window, len(all_w), len(sub), top, quotes, conf, signals)
        valid = {r.review_id for r in all_w}
        if conf:
            valid |= set(conf["review_ids"])
        prv = review_pulse(md, top, quotes, window, valid)
        _step(run_id, "pulse", "ok" if prv.passed else "fail", {"words": word_count(md), "flags": [f.code for f in prv.flags]})

        explainer, erv = (build_explainer(conf) if conf else (None, {"passed": False, "flags": [{"code": "NO_FEE_CONFUSION"}]}))
        if explainer:
            explainer["pulse_run_id"] = run_id
        _step(run_id, "fee_explainer", "ok" if erv.get("passed") else "fail", {"flags": [f["code"] for f in erv.get("flags", [])]})

        stats = {"reviews_in_window": len(all_w), "substantive": len(sub), "ratings": dict(Counter(r.rating for r in all_w)),
                 "theme_method": cl["method"]}
        db.update("pulse_runs", run_id,
                  themes={"themes": themes, "top3": [t["id"] for t in top], "quotes": quotes, "method": cl["method"]},
                  fee_confusion=conf or {}, signals=signals,
                  pulse={"markdown": md, "words": word_count(md), "review": prv.model_dump()},
                  explainer={"draft": explainer, "review": erv}, review={"pulse": prv.model_dump(), "explainer": erv},
                  stats=stats)

        # ---- pending actions (each approved separately; nothing executes here)
        created = []
        if prv.passed:
            title = f"Weekly Product Pulse — {window['start']} to {window['end']}"
            created.append(gate.create("doc_append", f"Append pulse to 'Weekly Product Pulse' doc",
                                       {"document": "weekly-product-pulse", "title": title, "body": md}, "pulse_run", run_id))
            body = (f"Hi team,\n\nHere is this week's product pulse ({window['start']} to {window['end']}).\n\n{md}\n\n"
                    "Evidence (review IDs, quotes) is attached in the Groww Pulse app. This is an internal draft for review.\n")
            created.append(gate.create("email_draft", "Create email draft: weekly pulse to Product Team",
                                       {"to": "Product Team (internal distribution list)", "subject": title, "body": body}, "pulse_run", run_id))
        if explainer and erv.get("passed"):
            created.append(gate.create("doc_append", "Append fee explainer to 'Customer Fee Explainers' doc",
                                       {"document": "customer-fee-explainers", "title": explainer["title"], "body": explainer["markdown"]},
                                       "pulse_run", run_id))
            created.append(gate.create("canonical_publish", f"Publish fee explainer as canonical answer ({explainer['fee_type']})",
                                       {k: explainer[k] for k in ("title", "fee_type", "scheme_scope", "bullets", "citations",
                                                                   "source_ids", "last_checked", "pulse_run_id")}, "pulse_run", run_id))
        _step(run_id, "pending_actions", detail={"created": created})
        db.update("pulse_runs", run_id, status="completed", completed_at=db.now())
        log.info("pulse run %s completed; %d pending actions", run_id, len(created))
    except Exception as e:
        log.error("pulse run %s failed: %s", run_id, traceback.format_exc()[-800:])
        _step(run_id, "error", "fail", {"error": f"{type(e).__name__}: {str(e)[:200]}"})
        db.update("pulse_runs", run_id, status="failed", error=f"{type(e).__name__}: {str(e)[:200]}", completed_at=db.now())
    finally:
        _run_lock.release()


def mark_interrupted() -> None:
    for r in db.all_("SELECT id FROM pulse_runs WHERE status='running'"):
        db.update("pulse_runs", r["id"], status="interrupted", completed_at=db.now())
