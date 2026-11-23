"""SQLite persistence (Railway volume). Every text write passes through a PII guard."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from config import APP_DB
from core.pii import contains_pii, redact

log = logging.getLogger("db")
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  channel TEXT NOT NULL,                -- typed | voice | eval
  text_redacted TEXT NOT NULL,
  pii_types TEXT NOT NULL DEFAULT '[]',
  intent TEXT, fee_type TEXT, scheme TEXT, team TEXT,
  status TEXT NOT NULL,                 -- processing | ready | blocked | approved | rejected | failed
  round INTEGER NOT NULL DEFAULT 1,
  current_draft_id INTEGER,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id INTEGER NOT NULL REFERENCES questions(id),
  version INTEGER NOT NULL,
  round INTEGER NOT NULL,
  attempt INTEGER NOT NULL,             -- 1 = first draft, 2 = named correction
  origin TEXT NOT NULL,                 -- generated | correction | human_edit | canonical | refinement
  reply TEXT NOT NULL,
  citations TEXT NOT NULL,
  last_checked TEXT,
  routing TEXT NOT NULL,
  review TEXT NOT NULL,
  passed INTEGER NOT NULL,
  agents TEXT NOT NULL,                 -- structured agent outputs snapshot (redacted)
  canonical_id INTEGER,
  correction_of INTEGER,
  correction_name TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id INTEGER, pulse_run_id INTEGER,
  round INTEGER, agent TEXT NOT NULL, status TEXT NOT NULL,
  duration_ms INTEGER, input_sha256 TEXT, output_summary TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pulse_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trigger TEXT NOT NULL, status TEXT NOT NULL,
  window_start TEXT, window_end TEXT,
  steps TEXT NOT NULL DEFAULT '[]',
  themes TEXT, fee_confusion TEXT, signals TEXT, pulse TEXT, explainer TEXT, review TEXT, stats TEXT,
  error TEXT, created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,                   -- doc_append | email_draft | canonical_publish
  title TEXT NOT NULL,
  target TEXT NOT NULL,
  payload TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  status TEXT NOT NULL,                 -- pending | executed | rejected | failed
  source_type TEXT, source_id INTEGER,
  decided_at TEXT, decided_by TEXT, result TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS canonical_explainers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fee_type TEXT NOT NULL, scheme_scope TEXT,
  title TEXT NOT NULL, bullets TEXT NOT NULL, citations TEXT NOT NULL,
  source_ids TEXT NOT NULL, source_hashes TEXT NOT NULL,
  last_checked TEXT, action_id INTEGER, pulse_run_id INTEGER,
  active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS canonical_reuses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  canonical_id INTEGER NOT NULL, question_id INTEGER NOT NULL, draft_id INTEGER, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL, ref_type TEXT, ref_id INTEGER, detail TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_q_intent ON questions(intent, created_at);
CREATE INDEX IF NOT EXISTS ix_d_q ON drafts(question_id);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(APP_DB, check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


_conn_singleton: sqlite3.Connection | None = None


def conn() -> sqlite3.Connection:
    global _conn_singleton
    if _conn_singleton is None:
        _conn_singleton = _conn()
    return _conn_singleton


def init_db() -> None:
    with _lock:
        conn().executescript(SCHEMA)
        conn().commit()
    scrub_pii()


def scrub_pii() -> int:
    """Re-redact stored text with the current detectors. Runs at startup so that when a
    detector is improved, rows written before the fix (e.g. a malformed PAN that slipped
    through) are cleaned too. Returns the number of cells changed; values are never logged."""
    changed = 0
    with tx() as c:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for t in tables:
            cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})") if (r[2] or "").upper() == "TEXT"]
            for row in c.execute(f"SELECT id, {', '.join(cols)} FROM {t}").fetchall() if cols else []:
                fixes = {}
                for col in cols:
                    v = row[col]
                    if isinstance(v, str) and contains_pii(v):
                        fixes[col] = redact(v).text
                if fixes:
                    sets = ",".join(f"{k}=?" for k in fixes)
                    c.execute(f"UPDATE {t} SET {sets} WHERE id=?", [*fixes.values(), row["id"]])
                    changed += len(fixes)
    if changed:
        log.warning("pii scrub: re-redacted %d stored cell(s)", changed)
    return changed


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    with _lock:
        c = conn()
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise


def _guard(values: dict[str, Any], table: str) -> dict[str, Any]:
    """Serialise JSON fields and refuse to persist PII anywhere."""
    out = {}
    for k, v in values.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        if isinstance(v, str):
            kinds = contains_pii(v)
            if kinds:
                raise ValueError(f"refusing to persist PII ({','.join(kinds)}) into {table}.{k}")
        out[k] = v
    return out


def insert(table: str, **values: Any) -> int:
    v = _guard(values, table)
    cols = ",".join(v)
    q = ",".join("?" for _ in v)
    with tx() as c:
        cur = c.execute(f"INSERT INTO {table} ({cols}) VALUES ({q})", list(v.values()))
        return int(cur.lastrowid)


def update(table: str, row_id: int, **values: Any) -> None:
    v = _guard(values, table)
    sets = ",".join(f"{k}=?" for k in v)
    with tx() as c:
        c.execute(f"UPDATE {table} SET {sets} WHERE id=?", [*v.values(), row_id])


def _decode(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, str) and v[:1] in "[{":
            try:
                d[k] = json.loads(v)
            except json.JSONDecodeError:
                pass
    return d


def one(sql: str, *args: Any) -> dict | None:
    with _lock:
        return _decode(conn().execute(sql, args).fetchone())


def all_(sql: str, *args: Any) -> list[dict]:
    with _lock:
        return [_decode(r) for r in conn().execute(sql, args).fetchall()]  # type: ignore[misc]


def event(kind: str, ref_type: str | None = None, ref_id: int | None = None, detail: Any = None) -> None:
    insert("events", kind=kind, ref_type=ref_type, ref_id=ref_id, detail=detail or {}, created_at=now())
