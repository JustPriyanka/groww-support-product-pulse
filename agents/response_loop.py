"""
User response loop controller.

submit()  : ingress redaction -> intent -> [facts || pattern || compliance] -> orchestrator
            -> reviewer -> (one named correction) -> ready | blocked
refine()  : <= 5 rounds; reruns only the affected components
edit()    : human edit, re-reviewed; failing edit is refused and nothing changes
approve() / reject()
"""
from __future__ import annotations

import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from agents import compliance as compliance_agent
from agents import facts as facts_agent
from agents import pattern as pattern_agent
from agents.orchestrator import (compose_from_canonical, compose_reply, find_canonical, last_checked_for, route,
                                 snapshot)
from agents.reviewer import review_reply
from agents.schemas import Citation, ComplianceOutput, FactsOutput, PatternOutput, ReviewResult
from config import MAX_REFINEMENT_ROUNDS
from core import db
from core.intents import classify
from core.pii import redact

log = logging.getLogger("response_loop")
_pool = ThreadPoolExecutor(max_workers=6)


class LoopError(Exception):
    def __init__(self, status: int, msg: str, extra: dict | None = None):
        super().__init__(msg)
        self.status, self.msg, self.extra = status, msg, extra or {}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _record(qid: int, rnd: int, agent: str, status: str, ms: int, input_text: str, summary: dict) -> None:
    db.insert("agent_runs", question_id=qid, round=rnd, agent=agent, status=status, duration_ms=ms,
              input_sha256=_sha(input_text), output_summary=summary, created_at=db.now())


def _timed(fn, *args, **kw):
    t0 = time.time()
    try:
        return fn(*args, **kw), int((time.time() - t0) * 1000), "ok"
    except Exception as e:  # agent failure must not take down the loop
        log.exception("agent failed: %s", fn.__module__)
        return e, int((time.time() - t0) * 1000), "error"


def _facts_summary(f: FactsOutput) -> dict:
    return {"status": f.status, "mode": f.mode, "n_facts": len(f.facts), "sources": sorted({x.source_id for x in f.facts}),
            "searched_sources": f.searched.get("sources_considered", [])}


def _run_agents(qid: int, rnd: int, text: str, ir, pii_types: list[str], which: set[str],
                prev: dict | None, extra_query: str = "") -> tuple[FactsOutput, PatternOutput, ComplianceOutput, list[str]]:
    """Run the requested agents IN PARALLEL; reuse previous outputs for the rest."""
    futures = {}
    if "facts" in which:
        futures["facts"] = _pool.submit(_timed, facts_agent.run, text, ir.intent, ir.fee_type, ir.scheme, extra_query)
    if "pattern" in which:
        futures["pattern"] = _pool.submit(_timed, pattern_agent.run, ir.intent, ir.fee_type)
    if "compliance" in which:
        futures["compliance"] = _pool.submit(_timed, compliance_agent.run, text, pii_types)
    results = {k: f.result() for k, f in futures.items()}
    ran = []
    out = {}
    for name, (res, ms, status) in results.items():
        ran.append(name)
        if status == "error":
            _record(qid, rnd, name, "error", ms, text, {"error": type(res).__name__})
            if name == "facts":
                res = FactsOutput(status="not_covered", searched={"error": "facts agent failed"}, topic="this question", note="agent error")
            elif name == "pattern":
                res = PatternOutput(intent=ir.intent, classification="isolated", review_count=0, review_window={}, recent_review_count=0,
                                    weekly_review_counts=[], sample_review_ids=[], matched_themes=[], question_count_7d=0,
                                    question_count_prev_7d=0, question_window={}, rationale="pattern agent error")
            else:
                res = compliance_agent.run(text, pii_types, use_llm=False)
        else:
            summ = (_facts_summary(res) if name == "facts" else
                    {"classification": res.classification, "review_count": res.review_count, "q7": res.question_count_7d}
                    if name == "pattern" else {"flags": res.flags, "llm_used": res.llm_used})
            _record(qid, rnd, name, "ok", ms, text, summ)
        out[name] = res
    f = out.get("facts") or FactsOutput(**prev["facts"])
    p = out.get("pattern") or PatternOutput(**prev["pattern"])
    c = out.get("compliance") or ComplianceOutput(**prev["compliance"])
    return f, p, c, ran


def _draft_cycle(qid: int, rnd: int, text: str, ir, facts: FactsOutput, pattern: PatternOutput, comp: ComplianceOutput,
                 *, feedback: str = "", fault: str | None = None, origin: str = "generated", allow_canonical: bool = True) -> dict:
    """orchestrator -> reviewer -> (one named correction) ; persists draft(s); returns final draft row."""
    canon = find_canonical(ir) if allow_canonical else None
    version = (db.one("SELECT MAX(version) v FROM drafts WHERE question_id=?", qid)["v"] or 0) + 1

    def orchestrate(attempt: int, fb: str) -> tuple[str, list[Citation], str]:
        t0 = time.time()
        if canon and attempt == 1 and not fb:
            reply, cits = compose_from_canonical(text, canon, comp)
            mode = "canonical"
        else:
            f = fault if (attempt == 1 or fault == "uncited_twice") else None
            reply, cits, mode = compose_reply(text, facts, comp, feedback=fb, fault=f)
        _record(qid, rnd, "orchestrator", "ok", int((time.time() - t0) * 1000), text,
                {"attempt": attempt, "mode": mode, "sentences_cited": len(cits)})
        return reply, cits, mode

    def review(reply: str, cits: list[Citation], lc: str, attempt: int) -> ReviewResult:
        t0 = time.time()
        r = review_reply(reply, cits, lc)
        _record(qid, rnd, "reviewer", "ok", int((time.time() - t0) * 1000), reply,
                {"attempt": attempt, "passed": r.passed, "flags": [f.code for f in r.flags]})
        return r

    canonical_used = bool(canon)
    reply, cits, mode = orchestrate(1, feedback)
    canonical_used = mode == "canonical"
    lc = last_checked_for(cits, facts)
    rv = review(reply, cits, lc, 1)
    routing = route(ir, facts, pattern, comp, canonical_used)
    snap = snapshot(facts, pattern, comp)
    first_id = db.insert("drafts", question_id=qid, version=version, round=rnd, attempt=1,
                         origin="canonical" if canonical_used else origin, reply=reply,
                         citations=[c.model_dump() for c in cits], last_checked=lc, routing=routing.model_dump(),
                         review=rv.model_dump(), passed=int(rv.passed), agents=snap,
                         canonical_id=canon["id"] if canonical_used else None, created_at=db.now())
    final_id, final_rv = first_id, rv
    if not rv.passed:
        codes = sorted({f.code for f in rv.flags})
        name = "correction:" + "+".join(codes)
        details = "; ".join(f"{f.code}: {f.detail}" + (f" in sentence '{f.sentence}'" if f.sentence else "") for f in rv.flags)
        reply2, cits2, _ = orchestrate(2, f"Previous draft failed review ({details}). Fix it: every sentence must cite facts and use only their numbers; remove anything else.")
        lc2 = last_checked_for(cits2, facts)
        rv2 = review(reply2, cits2, lc2, 2)
        final_id = db.insert("drafts", question_id=qid, version=version + 1, round=rnd, attempt=2, origin="correction",
                             reply=reply2, citations=[c.model_dump() for c in cits2], last_checked=lc2,
                             routing=routing.model_dump(), review=rv2.model_dump(), passed=int(rv2.passed), agents=snap,
                             correction_of=first_id, correction_name=name, created_at=db.now())
        final_rv = rv2
    status = "ready" if final_rv.passed else "blocked"
    db.update("questions", qid, status=status, current_draft_id=final_id, updated_at=db.now())
    if canonical_used and final_rv.passed:
        db.insert("canonical_reuses", canonical_id=canon["id"], question_id=qid, draft_id=final_id, created_at=db.now())
    log.info("question=%s round=%s status=%s intent=%s", qid, rnd, status, ir.intent)
    return db.one("SELECT * FROM drafts WHERE id=?", final_id)


# --------------------------------------------------------------------------- public API
def submit(raw_text: str, channel: str = "typed", fault: str | None = None) -> dict:
    red = redact(raw_text or "")
    text = " ".join(red.text.split())
    del raw_text  # the raw value is not referenced again
    meaningful = [w for w in text.split() if "_REDACTED]" not in w]
    if len(meaningful) < 3:
        raise LoopError(422, "Message is too short or contained only personal details; nothing was stored.",
                        {"pii_types": red.found})
    ir = classify(text)
    if ir.intent == "voice_command_blocked":
        raise LoopError(422, "Commands such as approve/reject/send cannot be given by voice or chat. Use the buttons on the Approvals screen.",
                        {"intent": ir.intent})
    qid = db.insert("questions", created_at=db.now(), channel=channel, text_redacted=text, pii_types=red.found,
                    intent=ir.intent, fee_type=ir.fee_type, scheme=ir.scheme, team=ir.team, status="processing", round=1)
    if red.found:
        log.info("question=%s pii_redacted_types=%s", qid, red.found)
    facts, pattern, comp, _ = _run_agents(qid, 1, text, ir, red.found, {"facts", "pattern", "compliance"}, None)
    _draft_cycle(qid, 1, text, ir, facts, pattern, comp, fault=fault)
    return get_question(qid)


FACT_WORDS = ("add", "include", "missing", "mention", "source", "fact", "detail", "explain", "also", "what about", "cite")


def refine(qid: int, feedback_raw: str) -> dict:
    q = db.one("SELECT * FROM questions WHERE id=?", qid)
    if not q:
        raise LoopError(404, "question not found")
    if q["status"] in ("approved", "rejected"):
        raise LoopError(409, f"question already {q['status']}")
    if q["round"] >= MAX_REFINEMENT_ROUNDS:
        raise LoopError(409, f"refinement limit ({MAX_REFINEMENT_ROUNDS} rounds) reached")
    fb = redact(feedback_raw or "")
    feedback = " ".join(fb.text.split())[:400]
    rnd = q["round"] + 1
    db.update("questions", qid, round=rnd, status="processing", updated_at=db.now())
    prev = db.one("SELECT agents FROM drafts WHERE id=?", q["current_draft_id"])["agents"]
    ir = classify(q["text_redacted"])
    which = {"facts"} if any(w in feedback.lower() for w in FACT_WORDS) else set()
    facts, pattern, comp, ran = _run_agents(qid, rnd, q["text_redacted"], ir, q["pii_types"], which, prev,
                                            extra_query=feedback if which else "")
    _draft_cycle(qid, rnd, q["text_redacted"], ir, facts, pattern, comp, feedback=feedback, origin="refinement",
                 allow_canonical=False)
    db.event("refine", "question", qid, {"round": rnd, "reran": ran + ["orchestrator", "reviewer"]})
    return get_question(qid)


def edit(draft_id: int, new_reply_raw: str) -> dict:
    d = db.one("SELECT * FROM drafts WHERE id=?", draft_id)
    if not d:
        raise LoopError(404, "draft not found")
    q = db.one("SELECT * FROM questions WHERE id=?", d["question_id"])
    if q["current_draft_id"] != draft_id:
        raise LoopError(409, "only the current draft can be edited")
    if q["status"] != "ready":
        raise LoopError(409, f"draft is {q['status']}; only passing drafts can be edited")
    red = redact(new_reply_raw or "")
    cits = [Citation(**c) for c in d["citations"]]
    rv = review_reply(new_reply_raw or "", cits, d["last_checked"])  # review the ORIGINAL edit text so PII is caught
    _record(q["id"], q["round"], "reviewer", "ok", 0, red.text, {"attempt": "human_edit", "passed": rv.passed,
                                                                  "flags": [f.code for f in rv.flags]})
    if not rv.passed:
        raise LoopError(422, "Edited draft failed review; the previous draft is unchanged.",
                        {"flags": [f.model_dump() for f in rv.flags]})
    version = (db.one("SELECT MAX(version) v FROM drafts WHERE question_id=?", q["id"])["v"] or 0) + 1
    nid = db.insert("drafts", question_id=q["id"], version=version, round=q["round"], attempt=1, origin="human_edit",
                    reply=red.text, citations=d["citations"], last_checked=d["last_checked"], routing=d["routing"],
                    review=rv.model_dump(), passed=1, agents=d["agents"], created_at=db.now())
    db.update("questions", q["id"], current_draft_id=nid, updated_at=db.now())
    return get_question(q["id"])


def approve(draft_id: int) -> dict:
    d = db.one("SELECT * FROM drafts WHERE id=?", draft_id)
    if not d:
        raise LoopError(404, "draft not found")
    q = db.one("SELECT * FROM questions WHERE id=?", d["question_id"])
    if q["current_draft_id"] != draft_id:
        raise LoopError(409, "only the current draft can be approved")
    if not d["passed"]:
        raise LoopError(409, "approval disabled: draft failed review", {"flags": d["review"]["flags"]})
    if q["status"] == "approved":
        return get_question(q["id"])
    if q["status"] != "ready":
        raise LoopError(409, f"question is {q['status']}")
    db.update("questions", q["id"], status="approved", updated_at=db.now())
    db.event("draft_approved", "draft", draft_id)
    return get_question(q["id"])


def reject(draft_id: int, reason: str = "") -> dict:
    d = db.one("SELECT * FROM drafts WHERE id=?", draft_id)
    if not d:
        raise LoopError(404, "draft not found")
    q = db.one("SELECT * FROM questions WHERE id=?", d["question_id"])
    if q["status"] in ("approved", "rejected"):
        raise LoopError(409, f"question already {q['status']}")
    db.update("questions", q["id"], status="rejected", updated_at=db.now())
    db.event("draft_rejected", "draft", draft_id, {"reason": redact(reason).text[:200]})
    return get_question(q["id"])


def get_question(qid: int) -> dict:
    q = db.one("SELECT * FROM questions WHERE id=?", qid)
    if not q:
        raise LoopError(404, "question not found")
    q["drafts"] = db.all_("SELECT * FROM drafts WHERE question_id=? ORDER BY version", qid)
    q["current_draft"] = next((d for d in q["drafts"] if d["id"] == q["current_draft_id"]), None)
    q["agent_runs"] = db.all_("SELECT id, round, agent, status, duration_ms, output_summary, created_at FROM agent_runs WHERE question_id=? ORDER BY id", qid)
    q["approval_enabled"] = bool(q["current_draft"] and q["current_draft"]["passed"] and q["status"] == "ready")
    return q
