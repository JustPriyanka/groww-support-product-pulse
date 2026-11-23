"""
Approval gate. Each pending action stores the exact payload + target that will be
written. Approving executes exactly that one action and nothing else.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

from actions import mcp_client
from config import APPROVAL_SECRET
from core import db
from core.corpus import get_corpus
from mcp_server.server import DOCUMENTS, payload_sha256

log = logging.getLogger("gate")

KINDS = {"doc_append", "email_draft", "canonical_publish"}


class GateError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status, self.msg = status, msg


def target_label(kind: str, payload: dict) -> str:
    if kind == "doc_append":
        return f"MCP append_doc_entry → document '{DOCUMENTS.get(payload['document'], payload['document'])}' ({payload['document']})"
    if kind == "email_draft":
        return f"MCP create_email_draft → draft addressed to '{payload['to']}' (saved as draft, never sent)"
    return f"Canonical answer store → fee '{payload['fee_type']}', scheme scope '{payload.get('scheme_scope') or 'all / platform-wide'}'"


def create(kind: str, title: str, payload: dict, source_type: str, source_id: int | None) -> int:
    assert kind in KINDS
    return db.insert("actions", kind=kind, title=title, target=target_label(kind, payload), payload=payload,
                     payload_sha256=payload_sha256(payload), status="pending", source_type=source_type,
                     source_id=source_id, created_at=db.now())


def _token(action_id: int, digest: str) -> str:
    return hmac.new(APPROVAL_SECRET.encode(), f"{action_id}:{digest}".encode(), hashlib.sha256).hexdigest()


def approve(action_id: int, seen_sha256: str, decided_by: str = "reviewer") -> dict:
    a = db.one("SELECT * FROM actions WHERE id=?", action_id)
    if not a:
        raise GateError(404, "action not found")
    if a["status"] != "pending":
        raise GateError(409, f"action is {a['status']}, not pending")
    if seen_sha256 != a["payload_sha256"] or payload_sha256(a["payload"]) != a["payload_sha256"]:
        raise GateError(409, "payload changed since you reviewed it; reload and review again")
    token = _token(action_id, a["payload_sha256"])
    p = a["payload"]
    try:
        if a["kind"] == "doc_append":
            res = mcp_client.call("append_doc_entry", {"action_id": action_id, "document": p["document"], "title": p["title"],
                                                       "body": p["body"], "approval_token": token})
        elif a["kind"] == "email_draft":
            res = mcp_client.call("create_email_draft", {"action_id": action_id, "to": p["to"], "subject": p["subject"],
                                                         "body": p["body"], "approval_token": token})
        else:
            res = _publish_canonical(action_id, p)
    except Exception as e:  # MCP subprocess failure
        log.exception("action %s execution failed", action_id)
        db.update("actions", action_id, status="failed", decided_at=db.now(), decided_by=decided_by, result={"error": str(e)[:300]})
        raise GateError(502, f"execution failed: {e}")
    status = "executed" if res.get("ok") else "failed"
    db.update("actions", action_id, status=status, decided_at=db.now(), decided_by=decided_by, result=res)
    db.event("action_" + status, "action", action_id, {"kind": a["kind"]})
    return db.one("SELECT * FROM actions WHERE id=?", action_id)


def _publish_canonical(action_id: int, p: dict) -> dict:
    corpus = get_corpus()
    hashes = {sid: corpus.sources[sid].sha256 for sid in p["source_ids"] if sid in corpus.sources}
    if len(hashes) != len(p["source_ids"]):
        return {"ok": False, "error": "a cited source is no longer in the corpus"}
    # one active canonical per (fee_type, scheme_scope)
    for old in db.all_("SELECT id FROM canonical_explainers WHERE active=1 AND fee_type=? AND IFNULL(scheme_scope,'')=?",
                       p["fee_type"], p.get("scheme_scope") or ""):
        db.update("canonical_explainers", old["id"], active=0)
    cid = db.insert("canonical_explainers", fee_type=p["fee_type"], scheme_scope=p.get("scheme_scope"), title=p["title"],
                    bullets=p["bullets"], citations=p["citations"], source_ids=p["source_ids"], source_hashes=hashes,
                    last_checked=p["last_checked"], action_id=action_id, pulse_run_id=p.get("pulse_run_id"), created_at=db.now())
    return {"ok": True, "canonical_id": cid}


def reject(action_id: int, decided_by: str = "reviewer") -> dict:
    a = db.one("SELECT * FROM actions WHERE id=?", action_id)
    if not a:
        raise GateError(404, "action not found")
    if a["status"] != "pending":
        raise GateError(409, f"action is {a['status']}, not pending")
    db.update("actions", action_id, status="rejected", decided_at=db.now(), decided_by=decided_by)
    return db.one("SELECT * FROM actions WHERE id=?", action_id)
