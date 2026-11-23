"""
FastAPI backend — Groww Support & Product Intelligence.

Run locally:   uvicorn api:app --reload --port 8000
Deploy:        Railway (see Docs/deployment-plan.md). Env: GROQ_API_KEY, ALLOWED_ORIGINS, DATA_DIR=/data, APPROVAL_SECRET
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import config
from core.logging_setup import setup_logging

setup_logging()

from actions import gate, mcp_client  # noqa: E402
from agents import response_loop as rl  # noqa: E402
from core import db  # noqa: E402
from core.corpus import get_corpus  # noqa: E402
from core.intents import FEE_TYPE_LABELS, SCHEME_NAMES  # noqa: E402
from core.reviews import all_reviews, by_id, dataset_window  # noqa: E402
from pipeline import scheduler, weekly  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    weekly.mark_interrupted()
    get_corpus()          # warm caches so the first request is fast
    all_reviews()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Groww Support & Product Intelligence API", lifespan=lifespan)

_extra = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://localhost:3000"] + _extra,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(rl.LoopError)
async def _loop_err(_: Request, e: rl.LoopError):
    return JSONResponse(status_code=e.status, content={"detail": e.msg, **e.extra})


@app.exception_handler(gate.GateError)
async def _gate_err(_: Request, e: gate.GateError):
    return JSONResponse(status_code=e.status, content={"detail": e.msg})


@app.exception_handler(Exception)
async def _any_err(_: Request, e: Exception):
    # never echo request content back; type only
    return JSONResponse(status_code=500, content={"detail": f"internal error ({type(e).__name__})"})


def reviewer_auth(x_reviewer_passcode: Optional[str] = Header(default=None)) -> str:
    if config.REVIEWER_PASSCODE and x_reviewer_passcode != config.REVIEWER_PASSCODE:
        raise HTTPException(401, "reviewer passcode required for this action")
    return "reviewer"


# --------------------------------------------------------------------------- meta
@app.get("/api/health")
def health():
    return {"status": "ok", "llm_configured": bool(config.GROQ_API_KEY), "next_scheduled_pulse": scheduler.next_run()}


@app.get("/api/meta")
def meta():
    c = get_corpus()
    s, e = dataset_window()
    return {
        "amc": "HDFC Mutual Fund", "schemes": SCHEME_NAMES, "fee_types": FEE_TYPE_LABELS,
        "corpus": {"sources": len(c.sources), "sentences": len(c.sentences),
                   "publishers": sorted({x.publisher for x in c.sources.values()}),
                   "last_checked": max(x.fetched_at for x in c.sources.values())},
        "reviews": {"count": len(all_reviews()), "window": {"start": s.isoformat(), "end": e.isoformat()}, "source": "Google Play (public)"},
        "limits": {"reply_sentences": config.MAX_REPLY_SENTENCES, "pulse_words": config.MAX_PULSE_WORDS,
                   "explainer_bullets": config.MAX_EXPLAINER_BULLETS, "refinement_rounds": config.MAX_REFINEMENT_ROUNDS,
                   "signal_threshold": config.SIGNAL_THRESHOLD},
        "schedule": {"cron": config.PULSE_CRON, "timezone": "Asia/Kolkata", "next_run": scheduler.next_run()},
        "passcode_required": bool(config.REVIEWER_PASSCODE),
        "models": {"reasoning": config.GROQ_MODEL, "fast": config.GROQ_FAST_MODEL},
    }


# --------------------------------------------------------------------------- response loop
class QuestionIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    channel: Literal["typed", "voice", "eval"] = "typed"


@app.post("/api/questions")
async def create_question(body: QuestionIn, x_eval_fault: Optional[str] = Header(default=None)):
    fault = x_eval_fault if config.ENABLE_EVAL_HOOKS else None
    return await asyncio.to_thread(rl.submit, body.text, body.channel, fault)


@app.get("/api/questions")
def list_questions(status: Optional[str] = None, limit: int = 200):
    rows = db.all_("SELECT q.*, d.reply, d.passed, d.routing, d.citations, d.review, d.origin, d.canonical_id, d.last_checked "
                   "FROM questions q LEFT JOIN drafts d ON d.id=q.current_draft_id "
                   + ("WHERE q.status=? " if status else "") + "ORDER BY q.id DESC LIMIT ?",
                   *([status] if status else []), limit)
    return {"questions": rows}


@app.get("/api/questions/{qid}")
def get_question(qid: int):
    return rl.get_question(qid)


class RefineIn(BaseModel):
    feedback: str = Field(min_length=1, max_length=600)


@app.post("/api/questions/{qid}/refine")
async def refine(qid: int, body: RefineIn, _=Depends(reviewer_auth)):
    return await asyncio.to_thread(rl.refine, qid, body.feedback)


class EditIn(BaseModel):
    reply: str = Field(min_length=1, max_length=2000)


@app.post("/api/drafts/{draft_id}/edit")
def edit_draft(draft_id: int, body: EditIn, _=Depends(reviewer_auth)):
    return rl.edit(draft_id, body.reply)


@app.post("/api/drafts/{draft_id}/approve")
def approve_draft(draft_id: int, _=Depends(reviewer_auth)):
    return rl.approve(draft_id)


class RejectIn(BaseModel):
    reason: str = ""


@app.post("/api/drafts/{draft_id}/reject")
def reject_draft(draft_id: int, body: RejectIn | None = None, _=Depends(reviewer_auth)):
    return rl.reject(draft_id, body.reason if body else "")


@app.post("/api/drafts/{draft_id}/propose-log")
def propose_log(draft_id: int, _=Depends(reviewer_auth)):
    """Create a PENDING action to append an approved reply to the support answers log."""
    d = db.one("SELECT * FROM drafts WHERE id=?", draft_id)
    if not d:
        raise HTTPException(404, "draft not found")
    q = db.one("SELECT * FROM questions WHERE id=?", d["question_id"])
    if q["status"] != "approved" or q["current_draft_id"] != draft_id:
        raise HTTPException(409, "only the approved current draft can be logged")
    existing = db.one("SELECT id FROM actions WHERE source_type='draft' AND source_id=? AND status IN ('pending','executed')", draft_id)
    if existing:
        raise HTTPException(409, f"already proposed as action {existing['id']}")
    srcs = "\n".join(f"[{c['n']}] {c['publisher']} — {c['title']} ({c['url']})" for c in d["citations"])
    body = (f"Question (redacted): {q['text_redacted']}\n\nApproved reply: {d['reply']}\n\nSources:\n{srcs or '—'}\n"
            f"Last checked: {d['last_checked']}\nRouting: {d['routing']['note']}")
    aid = gate.create("doc_append", f"Append approved reply #{q['id']} to support answers log",
                      {"document": "support-answers-log", "title": f"Q{q['id']} · {q['intent']}", "body": body}, "draft", draft_id)
    return db.one("SELECT * FROM actions WHERE id=?", aid)


# --------------------------------------------------------------------------- weekly loop
class PulseRunIn(BaseModel):
    window_days: int = Field(default=config.PULSE_WINDOW_DAYS, ge=3, le=28)
    end: Optional[date] = None


@app.post("/api/pulse/run")
def run_pulse(body: PulseRunIn | None = None, _=Depends(reviewer_auth)):
    body = body or PulseRunIn()
    try:
        rid = weekly.run("manual", end=body.end, window_days=body.window_days)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"run_id": rid, "status": "running"}


@app.get("/api/pulse/runs")
def pulse_runs(limit: int = 20):
    return {"runs": db.all_("SELECT id, trigger, status, window_start, window_end, created_at, completed_at, error FROM pulse_runs ORDER BY id DESC LIMIT ?", limit)}


@app.get("/api/pulse/runs/{run_id}")
def pulse_run(run_id: int):
    r = db.one("SELECT * FROM pulse_runs WHERE id=?", run_id)
    if not r:
        raise HTTPException(404, "run not found")
    r["actions"] = db.all_("SELECT * FROM actions WHERE source_type='pulse_run' AND source_id=? ORDER BY id", run_id)
    return r


@app.get("/api/pulse/latest")
def pulse_latest():
    r = db.one("SELECT id FROM pulse_runs WHERE status='completed' ORDER BY id DESC LIMIT 1")
    return pulse_run(r["id"]) if r else {"id": None}


# --------------------------------------------------------------------------- actions / approvals
@app.get("/api/actions")
def list_actions(status: Optional[str] = None):
    rows = db.all_("SELECT * FROM actions " + ("WHERE status=? " if status else "") + "ORDER BY id DESC", *([status] if status else []))
    return {"actions": rows}


@app.get("/api/actions/{action_id}")
def get_action(action_id: int):
    a = db.one("SELECT * FROM actions WHERE id=?", action_id)
    if not a:
        raise HTTPException(404, "action not found")
    return a


class ApproveIn(BaseModel):
    payload_sha256: str
    confirm: bool


@app.post("/api/actions/{action_id}/approve")
def approve_action(action_id: int, body: ApproveIn, who=Depends(reviewer_auth)):
    if not body.confirm:
        raise HTTPException(400, "explicit confirm=true required")
    return gate.approve(action_id, body.payload_sha256, who)


@app.post("/api/actions/{action_id}/reject")
def reject_action(action_id: int, who=Depends(reviewer_auth)):
    return gate.reject(action_id, who)


# --------------------------------------------------------------------------- canonical / sources / reviews
@app.get("/api/canonical")
def canonical():
    rows = db.all_("SELECT * FROM canonical_explainers ORDER BY id DESC")
    for r in rows:
        r["reuses"] = db.all_("SELECT cr.*, q.text_redacted, q.intent, q.scheme, q.status FROM canonical_reuses cr "
                              "JOIN questions q ON q.id=cr.question_id WHERE cr.canonical_id=? ORDER BY cr.id DESC", r["id"])
    return {"canonical": rows}


@app.get("/api/sources")
def sources():
    c = get_corpus()
    counts: dict[str, int] = {}
    for s in c.sentences.values():
        counts[s.source_id] = counts.get(s.source_id, 0) + 1
    return {"sources": [{**s.__dict__, "topics": list(s.topics), "sentences": counts.get(s.id, 0)} for s in c.sources.values()]}


@app.get("/api/sources/sentences")
def sentences(ids: str):
    c = get_corpus()
    out = []
    for sid in ids.split(",")[:50]:
        s = c.resolve(sid.strip())
        if s:
            src = c.sources[s.source_id]
            out.append({"id": s.sid, "text": s.text, "source_id": src.id, "url": src.url, "title": src.title,
                        "publisher": src.publisher, "last_checked": src.fetched_at})
    return {"sentences": out}


@app.get("/api/reviews")
def reviews(ids: str):
    m = by_id()
    out = []
    for rid in ids.split(",")[:300]:
        r = m.get(rid.strip())
        if r:
            out.append({"review_id": r.review_id, "date": r.date.isoformat(), "rating": r.rating, "text": r.text,
                        "source_url": r.source_url, "intent": r.intent})
    return {"reviews": out}


# --------------------------------------------------------------------------- workspace (read via MCP tools)
@app.get("/api/workspace")
async def workspace():
    docs = await asyncio.to_thread(mcp_client.call, "list_documents", {})
    contents = {}
    for d in docs:
        contents[d["document"]] = await asyncio.to_thread(mcp_client.call, "read_document", {"document": d["document"]})
    emails = await asyncio.to_thread(mcp_client.call, "list_email_drafts", {})
    return {"documents": docs, "contents": contents, "email_drafts": emails}


# --------------------------------------------------------------------------- observability
@app.get("/api/agent-runs")
def agent_runs(limit: int = 200):
    return {"runs": db.all_("SELECT * FROM agent_runs ORDER BY id DESC LIMIT ?", limit)}


@app.get("/api/stats")
def stats():
    q = db.all_("SELECT status, COUNT(*) n FROM questions GROUP BY status")
    a = db.all_("SELECT status, COUNT(*) n FROM actions GROUP BY status")
    return {"questions": {r["status"]: r["n"] for r in q}, "actions": {r["status"]: r["n"] for r in a},
            "canonical": db.one("SELECT COUNT(*) n FROM canonical_explainers WHERE active=1")["n"],
            "reuses": db.one("SELECT COUNT(*) n FROM canonical_reuses")["n"]}


# --------------------------------------------------------------------------- eval-only hooks
def _eval_only():
    if not config.ENABLE_EVAL_HOOKS:
        raise HTTPException(404, "not found")


@app.get("/api/debug/export")
def debug_export(_=Depends(_eval_only)):
    tables = ["questions", "drafts", "agent_runs", "pulse_runs", "actions", "canonical_explainers", "canonical_reuses", "events"]
    return {t: db.all_(f"SELECT * FROM {t}") for t in tables}


@app.get("/api/debug/logs")
def debug_logs(lines: int = 2000, _=Depends(_eval_only)):
    try:
        with open(config.LOG_FILE, encoding="utf-8") as f:
            return {"lines": f.readlines()[-lines:]}
    except FileNotFoundError:
        return {"lines": []}
