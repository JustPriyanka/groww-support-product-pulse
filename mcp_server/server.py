"""
Groww workspace MCP server (stdio).

A self-contained replacement for Google Docs / Gmail so the deployed prototype needs no
Google account. It is the ONLY component that writes documents and email drafts.

Tools
  append_doc_entry(action_id, document, title, body, approval_token)
  create_email_draft(action_id, to, subject, body, approval_token)
  list_documents() / read_document(document) / list_email_drafts()

Safety
  * Every write requires approval_token = HMAC_SHA256(APPROVAL_SECRET, f"{action_id}:{payload_sha256}")
    where payload_sha256 is recomputed HERE from the received arguments — so the content
    written is exactly the content that was approved, for exactly one action.
  * action_id is UNIQUE: a token can never be replayed and one approval can never write twice.
  * There is intentionally NO send-email tool. Drafts stay drafts.
  * Content is re-scanned for PII and refused if any is found.

Run standalone (e.g. from an MCP client):  python -m mcp_server.server
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from core.pii import contains_pii  # noqa: E402

DB_PATH = Path(os.environ.get("WORKSPACE_DB", ROOT / "data" / "state" / "workspace.db"))
SECRET = os.environ.get("APPROVAL_SECRET", "dev-only-secret").encode()

DOCUMENTS = {
    "weekly-product-pulse": "Weekly Product Pulse",
    "customer-fee-explainers": "Customer Fee Explainers",
    "support-answers-log": "Approved Support Answers Log",
}

server = MCPServer("groww-workspace", instructions="Approval-gated document and email-draft workspace. No send capability.")


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS doc_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, action_id INTEGER UNIQUE NOT NULL,
      document TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, payload_sha256 TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS email_drafts (id INTEGER PRIMARY KEY AUTOINCREMENT, action_id INTEGER UNIQUE NOT NULL,
      to_label TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
      payload_sha256 TEXT NOT NULL, created_at TEXT NOT NULL);
    """)
    return c


def payload_sha256(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _verify(action_id: int, payload: dict, token: str) -> str:
    digest = payload_sha256(payload)
    expected = hmac.new(SECRET, f"{action_id}:{digest}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, token or ""):
        raise PermissionError("approval token invalid for this action/payload")
    pii = contains_pii(json.dumps(payload, ensure_ascii=False))
    if pii:
        raise PermissionError(f"refusing to write content containing PII ({pii})")
    return digest


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@server.tool()
def append_doc_entry(action_id: int, document: str, title: str, body: str, approval_token: str) -> str:
    """Append ONE approved entry to a workspace document. Requires the approval token for this exact action and content."""
    if document not in DOCUMENTS:
        return json.dumps({"ok": False, "error": f"unknown document {document}"})
    payload = {"document": document, "title": title, "body": body}
    try:
        digest = _verify(action_id, payload, approval_token)
        with _db() as c:
            cur = c.execute("INSERT INTO doc_entries (action_id, document, title, body, payload_sha256, created_at) VALUES (?,?,?,?,?,?)",
                            (action_id, document, title, body, digest, _now()))
            return json.dumps({"ok": True, "entry_id": cur.lastrowid, "document": document, "document_title": DOCUMENTS[document],
                               "payload_sha256": digest})
    except sqlite3.IntegrityError:
        return json.dumps({"ok": False, "error": "action already executed (replay refused)"})
    except PermissionError as e:
        return json.dumps({"ok": False, "error": str(e)})


@server.tool()
def create_email_draft(action_id: int, to: str, subject: str, body: str, approval_token: str) -> str:
    """Create ONE email DRAFT (never sent). Requires the approval token for this exact action and content."""
    payload = {"to": to, "subject": subject, "body": body}
    try:
        digest = _verify(action_id, payload, approval_token)
        with _db() as c:
            cur = c.execute("INSERT INTO email_drafts (action_id, to_label, subject, body, payload_sha256, created_at) VALUES (?,?,?,?,?,?)",
                            (action_id, to, subject, body, digest, _now()))
            return json.dumps({"ok": True, "draft_id": cur.lastrowid, "status": "draft", "sent": False, "payload_sha256": digest})
    except sqlite3.IntegrityError:
        return json.dumps({"ok": False, "error": "action already executed (replay refused)"})
    except PermissionError as e:
        return json.dumps({"ok": False, "error": str(e)})


@server.tool()
def list_documents() -> str:
    """List workspace documents with entry counts."""
    with _db() as c:
        counts = {r["document"]: r["n"] for r in c.execute("SELECT document, COUNT(*) n FROM doc_entries GROUP BY document")}
    return json.dumps([{"document": k, "title": v, "entries": counts.get(k, 0)} for k, v in DOCUMENTS.items()])


@server.tool()
def read_document(document: str) -> str:
    """Read all entries of a workspace document (oldest first)."""
    with _db() as c:
        rows = [dict(r) for r in c.execute("SELECT id, action_id, title, body, payload_sha256, created_at FROM doc_entries WHERE document=? ORDER BY id", (document,))]
    return json.dumps({"document": document, "title": DOCUMENTS.get(document, document), "entries": rows})


@server.tool()
def list_email_drafts() -> str:
    """List email drafts (all have status 'draft'; this server cannot send email)."""
    with _db() as c:
        rows = [dict(r) for r in c.execute("SELECT id, action_id, to_label, subject, body, status, payload_sha256, created_at FROM email_drafts ORDER BY id")]
    return json.dumps(rows)


if __name__ == "__main__":
    server.run("stdio")
