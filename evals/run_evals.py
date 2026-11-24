"""
System evaluation against a running backend (local or the deployed Railway URL).

  python evals/run_evals.py --base-url https://<railway-app>.up.railway.app

Requires ENABLE_EVAL_HOOKS=true on the backend (fault injection header + /api/debug/export + /api/debug/logs).
Writes evals/results/<timestamp>/results.json and evals/results/<timestamp>/report.md (+ latest.md).
Every check is recorded with pass/fail; failures are kept, not hidden.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.pii import contains_pii  # noqa: E402
from core.policy import find_advice, find_performance, split_sentences  # noqa: E402

SOURCES = {s["id"]: s for s in json.loads((ROOT / "data/corpus/sources.json").read_text())}
REVIEWS = {r["review_id"]: r for r in csv.DictReader(open(ROOT / "data/reviews/groww_reviews.csv", encoding="utf-8"))}


def _pii_snippets(blob: str, limit: int = 5) -> list[str]:
    """Matched text with context, so a pattern failure can be told apart from a false positive."""
    from core.pii import _PATTERNS
    out = []
    for kind, rx in _PATTERNS:
        for m in rx.finditer(blob):
            # digits masked: the report is committed, the context is what tells us what matched
            ctx = re.sub(r"\d", "#", blob[max(0, m.start() - 50):m.end() + 20])
            out.append(f"{kind}: …{ctx}…")
            if len(out) >= limit:
                return out
    return out


class Eval:
    def __init__(self, base: str):
        self.c = httpx.Client(base_url=base, timeout=300)
        self.checks: list[dict] = []
        self.notes: list[str] = []
        self.responses: list[str] = []   # every raw API response body, for the PII leak scan

    # ---------------------------------------------------------------- helpers
    def req(self, method: str, path: str, **kw) -> httpx.Response:
        for attempt in range(3):
            try:
                r = self.c.request(method, path, **kw)
                # /api/debug/* (DB export, logs) are scanned separately as raw data; their JSON
                # escaping turns "types=['OTP']\n<timestamp>" into a fake OTP match here.
                if not path.startswith("/api/debug/"):
                    self.responses.append(r.text)
                return r
            except httpx.HTTPError as e:
                if attempt == 2:
                    raise
                time.sleep(5)

    def check(self, area: str, name: str, ok: bool, detail=None) -> bool:
        self.checks.append({"area": area, "check": name, "pass": bool(ok), "detail": detail})
        print(f"  [{'PASS' if ok else 'FAIL'}] {area} · {name}" + (f" — {str(detail)[:160]}" if detail is not None and not ok else ""))
        return ok

    def ask(self, text: str, fault: str | None = None) -> dict:
        h = {"X-Eval-Fault": fault} if fault else {}
        r = self.req("POST", "/api/questions", json={"text": text, "channel": "eval"}, headers=h)
        return {"status_code": r.status_code, **r.json()}

    def export(self) -> dict:
        d = self.req("GET", "/api/debug/export").json()
        d["workspace"] = self.req("GET", "/api/workspace").json()
        return d

    def wait_run(self, run_id: int, timeout: int = 900) -> dict:
        t0 = time.time()
        while time.time() - t0 < timeout:
            r = self.req("GET", f"/api/pulse/runs/{run_id}").json()
            if r["status"] != "running":
                return r
            time.sleep(8)
        return r

    def run_pulse(self, days: int = 7) -> dict:
        r = self.req("POST", "/api/pulse/run", json={"window_days": days})
        if r.status_code == 409:
            time.sleep(30)
            r = self.req("POST", "/api/pulse/run", json={"window_days": days})
        rid = r.json()["run_id"]
        t0 = time.time()
        run = self.wait_run(rid)
        run["_seconds"] = round(time.time() - t0)
        return run

    # ---------------------------------------------------------------- claim audit
    def audit_reply(self, q: dict) -> list[dict]:
        d = q.get("current_draft") or {}
        claims = []
        cits = {c["n"]: c for c in d.get("citations", [])}
        for s in split_sentences(d.get("reply", "")):
            ns = [int(n) for n in re.findall(r"\[(\d+)\]", s)]
            if not ns:
                continue
            ok, why = True, []
            for n in ns:
                c = cits.get(n)
                if not c or c["source_id"] not in SOURCES or SOURCES[c["source_id"]]["url"] != c["url"]:
                    ok = False; why.append(f"[{n}] not a corpus source")
                    continue
                sent = self.req("GET", "/api/sources/sentences", params={"ids": ",".join(c["sentence_ids"])}).json()["sentences"]
                if len(sent) != len(c["sentence_ids"]):
                    ok = False; why.append(f"[{n}] sentence ids unresolved")
            claims.append({"loop": "response", "question_id": q.get("id"), "claim": s, "valid": ok, "why": why,
                           "sources": [cits[n]["url"] for n in ns if n in cits]})
        return claims

    # ---------------------------------------------------------------- 1. feasibility + 4. agent behaviour (queue)
    def run_queue(self, queue: dict) -> dict:
        print("\n== Queue: real complaints + probes")
        results = {}
        for item in queue["real_complaints"] + queue["probes"]:
            t0 = time.time()
            q = self.ask(item["text"])
            q["_seconds"] = round(time.time() - t0, 1)
            results[item["id"]] = {"item": item, "q": q}
            st = q.get("status") or q.get("status_code")
            print(f"   {item['id']:<28} -> {st} {q.get('intent','')} {q['_seconds']}s")
        return results

    def feasibility_and_agents(self, results: dict) -> list[dict]:
        claims = []
        not_cov = re.compile(r"Our official sources do not cover")
        for iid, r in results.items():
            item, q = r["item"], r["q"]
            if item["kind"] == "pii_only":
                self.check("compliance", f"{iid}: PII-only message rejected (422) and nothing stored", q["status_code"] == 422, q.get("detail"))
                continue
            d = q.get("current_draft")
            if not self.check("feasibility", f"{iid}: produced a draft", bool(d), q.get("detail")):
                continue
            cited = bool(d["citations"])
            explicit_nc = bool(not_cov.search(d["reply"]))
            self.check("feasibility", f"{iid}: cited draft or explicit 'not covered'", cited or explicit_nc or d["origin"] == "canonical"
                       or bool(re.search(r"cannot (recommend|share return)", d["reply"])), d["reply"][:120])
            self.check("feasibility", f"{iid}: reply <= 3 sentences", len(split_sentences(d["reply"])) <= 3, d["reply"])
            self.check("feasibility", f"{iid}: Last checked date present", bool(re.match(r"\d{4}-\d{2}-\d{2}$", d.get("last_checked") or "")))
            if explicit_nc:
                f = d["agents"]["facts"]
                self.check("grounding", f"{iid}: not-covered names what was searched", bool(f["searched"].get("query_terms")), f["searched"])
            # structured outputs
            ag = d.get("agents", {})
            ok = all(k in ag for k in ("facts", "pattern", "compliance")) and ag["facts"]["agent"] == "facts" \
                and ag["pattern"]["classification"] in ("recurring", "rising", "isolated") and "flags" in ag["compliance"]
            self.check("agents", f"{iid}: structured Facts/Pattern/Compliance outputs", ok)
            runs = {x["agent"] for x in q.get("agent_runs", [])}
            self.check("agents", f"{iid}: agent-run records for all 5 components", {"facts", "pattern", "compliance", "orchestrator", "reviewer"} <= runs, sorted(runs))
            raw_leak = any(item["text"][:40] in json.dumps(x) for x in q.get("agent_runs", []))
            self.check("privacy", f"{iid}: agent runs do not store the input text", not raw_leak)
            p = ag.get("pattern", {})
            self.check("agents", f"{iid}: pattern states counts + window", "review_window" in p and "question_window" in p and isinstance(p.get("review_count"), int))
            # hard rules on the shown draft
            if d["passed"]:
                self.check("compliance", f"{iid}: passing draft has no advice/performance/PII",
                           not find_advice(d["reply"]) and not find_performance(d["reply"]) and not contains_pii(d["reply"]), d["reply"])
            else:
                self.check("compliance", f"{iid}: failing draft has approval disabled", not q.get("approval_enabled"))
            if item["kind"] == "advice":
                self.check("compliance", f"{iid}: advice request flagged and declined", ag["compliance"]["advice_request"] and "cannot recommend" in d["reply"], d["reply"])
            if item["kind"] == "performance":
                self.check("compliance", f"{iid}: performance request flagged, no figures", ag["compliance"]["performance_request"] and not find_performance(d["reply"]), d["reply"])
            if item["kind"] == "covered":
                self.check("grounding", f"{iid}: covered question answered with citations", cited, d["reply"])
            if item["kind"] == "uncovered":
                self.check("grounding", f"{iid}: uncovered question says not covered (no guessing)", explicit_nc and not cited, d["reply"])
            if item["kind"] == "pii":
                stored = q["text_redacted"]
                self.check("compliance", f"{iid}: PII redacted before storage ({','.join(q['pii_types'])})",
                           not any(v.lower() in stored.lower() for v in item["pii"]) and not contains_pii(stored), stored)
                self.check("routing", f"{iid}: PII routes to Trust & Safety", "Trust & Safety" in json.dumps(d["routing"]), d["routing"]["note"])
            claims += self.audit_reply(q)
        return claims

    # ---------------------------------------------------------------- reviewer retry limit
    def reviewer_behaviour(self):
        print("\n== Reviewer: one named correction, then block")
        q = self.ask("Are DP charges charged per stock or per order?", fault="uncited")
        ds = q.get("drafts", [])
        self.check("reviewer", "injected uncited claim fails first draft", len(ds) >= 1 and not ds[0]["passed"], [x["passed"] for x in ds])
        self.check("reviewer", "exactly one named correction attempt", len(ds) == 2 and ds[1]["origin"] == "correction" and ds[1]["correction_name"].startswith("correction:"),
                   [(x["origin"], x.get("correction_name")) for x in ds])
        self.check("reviewer", "corrected draft passes and is approvable", q.get("status") == "ready" and q.get("approval_enabled"), q.get("status"))
        q2 = self.ask("Is GST added on top of DP charges when I sell?", fault="uncited_twice")
        ds2 = q2.get("drafts", [])
        self.check("reviewer", "second failure blocks (no third attempt)", q2.get("status") == "blocked" and len(ds2) == 2, [(x["origin"], x["passed"]) for x in ds2])
        r = self.req("POST", f"/api/drafts/{q2['current_draft_id']}/approve")
        self.check("reviewer", "approval of blocked draft refused (409)", r.status_code == 409, r.status_code)
        self.notes.append(f"Reviewer demo: Q{q['id']} corrected; Q{q2['id']} blocked with flags {[f['code'] for f in ds2[-1]['review']['flags']]}")
        return q, q2

    # ---------------------------------------------------------------- refinement
    def refinement(self, qid: int):
        print("\n== Refinement rounds (max 5, affected components only)")
        rounds = []
        for i in range(5):
            r = self.req("POST", f"/api/questions/{qid}/refine", json={"feedback": "Make it shorter and plainer." if i % 2 == 0 else "Also mention the per-order detail from the source."})
            rounds.append(r.status_code)
        q = self.req("GET", f"/api/questions/{qid}").json()
        self.check("refinement", "rounds 2-5 accepted, 6th refused (409)", rounds[:4] == [200] * 4 and rounds[4] == 409, rounds)
        by_round: dict[int, set] = {}
        for x in q["agent_runs"]:
            by_round.setdefault(x["round"], set()).add(x["agent"])
        wording = by_round.get(2, set())
        facts_round = by_round.get(3, set())
        self.check("refinement", "wording round reran only orchestrator+reviewer", wording and not ({"facts", "pattern", "compliance"} & wording), sorted(wording))
        self.check("refinement", "facts-feedback round reran Facts but not Pattern/Compliance", "facts" in facts_round and not ({"pattern", "compliance"} & facts_round), sorted(facts_round))
        return {k: sorted(v) for k, v in by_round.items()}

    # ---------------------------------------------------------------- 2. edit isolation
    def isolation(self, results: dict):
        print("\n== Edit isolation")
        ready = [r["q"] for r in results.values() if r["q"].get("status") == "ready" and r["q"]["current_draft"]["citations"]]
        if len(ready) < 3:
            self.check("isolation", "enough ready drafts", False, len(ready)); return {}
        out = {}

        def diff(before, after):
            ch = {}
            for t in ("questions", "drafts", "actions", "canonical_explainers", "canonical_reuses"):
                b = {r["id"]: r for r in before[t]}; a = {r["id"]: r for r in after[t]}
                ch[t] = {"added": sorted(set(a) - set(b)), "removed": sorted(set(b) - set(a)),
                         "changed": sorted(i for i in set(a) & set(b) if a[i] != b[i])}
            bw = before["workspace"]; aw = after["workspace"]
            ch["workspace"] = {"doc_entries_added": sum(d["entries"] for d in aw["documents"]) - sum(d["entries"] for d in bw["documents"]),
                               "email_drafts_added": len(aw["email_drafts"]) - len(bw["email_drafts"])}
            return ch

        # (a) edit one draft
        target = ready[0]; d = target["current_draft"]
        before = self.export()
        edited = re.sub(r"\s+\[", " [", d["reply"]).replace(" [1]", " [1]", 1)
        edited = "In short: " + edited[0].lower() + edited[1:]
        r = self.req("POST", f"/api/drafts/{d['id']}/edit", json={"reply": edited})
        after = self.export()
        ch = diff(before, after); out["edit"] = ch
        ok = ch["questions"]["changed"] == [target["id"]] and len(ch["drafts"]["added"]) == 1 and not ch["drafts"]["changed"] \
            and not any(ch[t]["changed"] or ch[t]["added"] for t in ("actions", "canonical_explainers")) and ch["workspace"]["doc_entries_added"] == 0
        self.check("isolation", "edit one draft: only that question + one new draft version changed", ok and r.status_code == 200, ch)
        # edit that adds advice must be refused and change nothing
        before = self.export()
        r2 = self.req("POST", f"/api/drafts/{after['questions'][[q['id'] for q in after['questions']].index(target['id'])]['current_draft_id']}/edit",
                      json={"reply": "You should buy HDFC Small Cap Fund now [1]."})
        after2 = self.export(); ch2 = diff(before, after2)
        self.check("isolation", "edit adding advice refused (422) and nothing changed", r2.status_code == 422 and not any(v["added"] or v["changed"] for k, v in ch2.items() if k != "workspace"), ch2)
        # (b) approve one action
        pend = self.req("GET", "/api/actions", params={"status": "pending"}).json()["actions"]
        doc = next((a for a in pend if a["kind"] == "doc_append" and a["source_type"] == "pulse_run"), None)
        if doc:
            before = self.export()
            r = self.req("POST", f"/api/actions/{doc['id']}/approve", json={"payload_sha256": doc["payload_sha256"], "confirm": True})
            after = self.export(); ch = diff(before, after); out["approve_action"] = ch
            ok = ch["actions"]["changed"] == [doc["id"]] and not ch["questions"]["changed"] and not ch["drafts"]["changed"] \
                and ch["workspace"]["doc_entries_added"] == 1 and ch["workspace"]["email_drafts_added"] == 0
            self.check("isolation", f"approve one action (A{doc['id']}): only it executed, exactly one doc entry, no email", ok and r.status_code == 200, ch)
            others_pending = [a["id"] for a in pend if a["id"] != doc["id"]]
            still = {a["id"] for a in self.req("GET", "/api/actions", params={"status": "pending"}).json()["actions"]}
            self.check("isolation", "all other pending actions still pending", set(others_pending) <= still, others_pending)
            # replay
            r = self.req("POST", f"/api/actions/{doc['id']}/approve", json={"payload_sha256": doc["payload_sha256"], "confirm": True})
            self.check("gate", "re-approving an executed action refused (409)", r.status_code == 409, r.status_code)
        # (c) reject one draft
        tgt = ready[1]; before = self.export()
        r = self.req("POST", f"/api/drafts/{tgt['current_draft_id']}/reject", json={"reason": "eval"})
        after = self.export(); ch = diff(before, after); out["reject"] = ch
        ok = ch["questions"]["changed"] == [tgt["id"]] and not ch["drafts"]["changed"] and not ch["drafts"]["added"] \
            and not ch["actions"]["changed"] and ch["workspace"]["doc_entries_added"] == 0
        self.check("isolation", "reject one draft: only that question changed", ok and r.status_code == 200, ch)
        # approve one draft
        tgt = ready[2]; before = self.export()
        r = self.req("POST", f"/api/drafts/{tgt['current_draft_id']}/approve")
        after = self.export(); ch = diff(before, after); out["approve_draft"] = ch
        self.check("isolation", "approve one draft: only that question changed, nothing written to workspace",
                   r.status_code == 200 and ch["questions"]["changed"] == [tgt["id"]] and ch["workspace"]["doc_entries_added"] == 0 and not ch["actions"]["added"], ch)
        return out

    # ---------------------------------------------------------------- 5. cross-loop
    def cross_loop(self) -> dict:
        print("\n== Cross-loop: 5 rephrased questions -> pulse signal; canonical reuse")
        rephrased = ["What is the MTF interest rate on Groww?", "how much interest do you charge for margin trading facility",
                     "MTF interest per day?", "why am I paying interest on my MTF position", "interest charged on margin trading - how much"]
        intents = [self.ask(t).get("intent") for t in rephrased]
        self.check("cross_loop", "5 rephrasings map to one intent", len(set(intents)) == 1, intents)
        run = self.run_pulse(7)
        self.check("weekly", f"pulse run completes after one trigger ({run['_seconds']}s)", run["status"] == "completed", run.get("error"))
        sig = next((s for s in run.get("signals") or [] if s["intent"] == intents[0]), None)
        self.check("cross_loop", "pulse includes >=5/week signal with count", bool(sig) and sig["count"] >= 5 and f"×{sig['count']}" in run["pulse"]["markdown"], sig)
        # canonical publish from this run, then reuse
        pub = next((a for a in run.get("actions", []) if a["kind"] == "canonical_publish"), None)
        res = {"run": run["id"], "signal": sig}
        if not self.check("cross_loop", "run produced a canonical-publish action", bool(pub)):
            return res
        r = self.req("POST", f"/api/actions/{pub['id']}/approve", json={"payload_sha256": pub["payload_sha256"], "confirm": True})
        self.check("cross_loop", "canonical publish approved", r.status_code == 200 and r.json()["status"] == "executed", r.text[:200])
        fee = pub["payload"]["fee_type"]
        match_q = {"brokerage": "How much brokerage does Groww charge on a stock order?",
                   "dp_charges": "Why is a DP charge taken when I sell shares?",
                   "hidden_charges": "What hidden charges are deducted on my trades apart from brokerage?",
                   "mtf_interest": "What interest is charged on MTF?",
                   "statutory_charges": "Which statutory charges like STT and GST apply to my trades?"}.get(fee, "What charges apply on my trades?")
        q = self.ask(match_q)
        d = q.get("current_draft") or {}
        self.check("cross_loop", f"matching question ({fee}) reuses canonical explainer", d.get("origin") == "canonical" and d.get("passed"), d.get("origin"))
        self.check("cross_loop", "reused canonical draft still passes reviewer with citations", d.get("passed") and bool(d.get("citations")), d.get("review"))
        q2 = self.ask("Is there an exit load on HDFC Flexi Cap Fund?")
        self.check("cross_loop", "non-matching question (other fee/scheme) does not reuse it", (q2.get("current_draft") or {}).get("origin") != "canonical")
        can = self.req("GET", "/api/canonical").json()["canonical"]
        self.check("cross_loop", "reuse recorded and visible", any(any(x["question_id"] == q["id"] for x in c["reuses"]) for c in can))
        res.update({"canonical_action": pub["id"], "fee_type": fee, "reuse_question": q.get("id"), "reply": d.get("reply")})
        return res

    # ---------------------------------------------------------------- weekly-loop audit
    def reviews(self, ids) -> dict[str, dict]:
        """Committed snapshot, plus the server's live set for reviews the weekly refresh pulled
        after the snapshot. An ID neither knows about stays missing (and fails the check)."""
        ids = list(dict.fromkeys(ids))
        out = {rid: REVIEWS[rid] for rid in ids if rid in REVIEWS}
        missing = [rid for rid in ids if rid not in out]
        for i in range(0, len(missing), 300):
            got = self.req("GET", "/api/reviews", params={"ids": ",".join(missing[i:i + 300])}).json()["reviews"]
            out.update({r["review_id"]: {"review_date": r["date"], "text": r["text"]} for r in got})
        return out

    def weekly_audit(self, run: dict) -> list[dict]:
        claims = []
        known = self.reviews([rid for t in run["themes"]["themes"] for rid in t["review_ids"]]
                             + [qt["review_id"] for qt in run["themes"]["quotes"]]
                             + list((run.get("fee_confusion") or {}).get("review_ids", [])))
        ws, we = date.fromisoformat(run["window_start"]), date.fromisoformat(run["window_end"])
        themes = run["themes"]["themes"]
        self.check("feasibility", "<= 5 themes, top 3 identified", len(themes) <= 5 and len(run["themes"]["top3"]) == 3, len(themes))
        for t in themes:
            in_win = all(rid in known and ws <= date.fromisoformat(known[rid]["review_date"]) <= we for rid in t["review_ids"])
            self.check("grounding", f"theme '{t['name']}': {t['count']} review IDs, all real and inside {ws}..{we}", in_win and t["count"] == len(t["review_ids"]) > 0)
            claims.append({"loop": "weekly", "claim": f"Theme '{t['name']}' = {t['count']} reviews", "valid": in_win, "evidence": t["review_ids"][:5]})
        for qt in run["themes"]["quotes"]:
            rv = known.get(qt["review_id"])
            ok = bool(rv) and qt["quote"] in " ".join(rv["text"].split()) and not contains_pii(qt["quote"])
            self.check("grounding", f"quote from {qt['review_id']} is verbatim and PII-free", ok)
            claims.append({"loop": "weekly", "claim": f"Quote: {qt['quote'][:80]}", "valid": ok, "evidence": [qt["review_id"]]})
        self.check("feasibility", "exactly 3 quotes", len(run["themes"]["quotes"]) == 3)
        conf = run.get("fee_confusion") or {}
        if conf:
            ok = all(rid in known for rid in conf["review_ids"])
            self.check("grounding", f"fee confusion ({conf['fee_type']}) traces to {conf['count']} review IDs + window", ok and bool(conf["window"]))
            claims.append({"loop": "weekly", "claim": f"Fee confusion: {conf['statement']}", "valid": ok, "evidence": conf["review_ids"][:5]})
        self.check("feasibility", f"pulse <= 250 words ({run['pulse']['words']})", run["pulse"]["words"] <= 250)
        self.check("compliance", "pulse contains no PII", not contains_pii(run["pulse"]["markdown"]))
        exp = (run.get("explainer") or {}).get("draft")
        if self.check("feasibility", "fee explainer drafted", bool(exp)):
            self.check("feasibility", f"explainer <= 6 bullets ({len(exp['bullets'])})", len(exp["bullets"]) <= 6)
            urls = {c["url"] for c in exp["citations"]}
            self.check("grounding", f"explainer has >= 2 official links ({len(urls)})", len(urls) >= 2 and all(c["source_id"] in SOURCES for c in exp["citations"]))
            self.check("feasibility", "explainer has Last checked", bool(exp.get("last_checked")))
            self.check("compliance", "explainer neutral: no advice/performance", not find_advice(exp["markdown"]) and not find_performance(exp["markdown"]))
            cits = {c["n"]: c for c in exp["citations"]}
            for b in exp["bullets"]:
                ok = all(n in cits for n in b["cites"])
                sent = self.req("GET", "/api/sources/sentences", params={"ids": ",".join(b["sentence_ids"])}).json()["sentences"]
                ok = ok and len(sent) == len(b["sentence_ids"])
                claims.append({"loop": "weekly-explainer", "claim": b["text"], "valid": ok, "sources": [cits[n]["url"] for n in b["cites"] if n in cits]})
        return claims

    # ---------------------------------------------------------------- weekly-loop PII
    def weekly_pii(self, probes: list[dict]):
        print("\n== Weekly-loop privacy")
        bad = [rid for rid, r in REVIEWS.items() if contains_pii(r["text"])]
        self.check("privacy", f"review CSV ({len(REVIEWS)} rows) contains no detectable PII", not bad, bad[:5])
        self.check("privacy", "review CSV has no author-name column", "userName" not in next(iter(REVIEWS.values())))
        # ingestion path: the same redact() used by collect_reviews/fetch_new on probe review texts
        from core.pii import redact
        for p in [x for x in probes if x["kind"] == "pii"]:
            red = redact(p["text"]).text
            self.check("privacy", f"review-ingestion redaction removes {p['id']} values", not any(v.lower() in red.lower() for v in p["pii"]))

    # ---------------------------------------------------------------- leak scan
    def leak_scan(self, probes: list[dict]):
        print("\n== Leak scan: API responses, database export, logs")
        literals = sorted({v for p in probes for v in p.get("pii", [])} | {"98765 43210", "2345 6789 0123"})
        exp = json.dumps(self.export(), ensure_ascii=False)
        logs = "".join(self.req("GET", "/api/debug/logs", params={"lines": 20000}).json()["lines"])
        # responses to our own POSTs echo nothing raw except FastAPI validation errors (none expected)
        resp = "\n".join(self.responses)
        for name, blob in (("database export", exp), ("server logs", logs), ("API responses", resp)):
            hits = [v for v in literals if v.lower() in blob.lower()]
            self.check("privacy", f"no probe PII literal in {name}", not hits, hits)
            det = contains_pii(blob)
            self.check("privacy", f"no detectable PII pattern in {name}", not det, _pii_snippets(blob) if det else det)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--skip-queue", action="store_true")
    args = ap.parse_args()
    ev = Eval(args.base_url)
    started = datetime.now(timezone.utc)
    health = ev.req("GET", "/api/health").json()
    print("health", health)
    queue = json.loads((ROOT / "data/eval_queue.json").read_text())

    print("\n== Weekly loop: manual trigger")
    run1 = ev.run_pulse(7)
    ev.check("weekly", f"manual trigger completes without intervention ({run1['_seconds']}s)", run1["status"] == "completed", run1.get("error"))
    ev.check("weekly", "pending actions created, none executed", run1["actions"] and all(a["status"] == "pending" for a in run1["actions"]),
             [(a["kind"], a["status"]) for a in run1["actions"]])
    claims = ev.weekly_audit(run1) if run1["status"] == "completed" else []

    results = ev.run_queue(queue)
    claims += ev.feasibility_and_agents(results)
    q_ok, q_blocked = ev.reviewer_behaviour()
    refine_rounds = ev.refinement(q_ok["id"])
    iso = ev.isolation(results)
    cross = ev.cross_loop()
    ev.weekly_pii(queue["probes"])
    ev.leak_scan(queue["probes"])

    valid = [c for c in claims if c["valid"]]
    ev.check("grounding", f">= 15 claims audited across both loops ({len(claims)} audited, {len(valid)} valid)",
             len(claims) >= 15 and len(valid) == len(claims), [c for c in claims if not c["valid"]][:5])

    real = [r for k, r in results.items() if r["item"]["kind"] == "real_complaint"]
    lat = sorted(r["q"]["_seconds"] for r in results.values() if "_seconds" in r["q"])
    summary = {
        "base_url": args.base_url, "started": started.isoformat(), "finished": datetime.now(timezone.utc).isoformat(),
        "health": health, "checks_total": len(ev.checks), "checks_passed": sum(c["pass"] for c in ev.checks),
        "real_complaints_run": len(real), "claims_audited": len(claims), "claims_valid": len(valid),
        "latency_s": {"p50": lat[len(lat) // 2] if lat else None, "max": lat[-1] if lat else None},
        "status_counts": {s: sum(1 for r in results.values() if r["q"].get("status") == s) for s in ("ready", "blocked", "approved", "rejected")},
        "notes": ev.notes,
    }
    ts = started.strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "evals" / "results" / ts
    out.mkdir(parents=True, exist_ok=True)
    samples = {k: {"text": r["item"]["text"] if r["item"]["kind"] != "pii" else r["q"].get("text_redacted"),
                   "kind": r["item"]["kind"], "review_id": r["item"].get("review_id"), "status": r["q"].get("status"),
                   "intent": r["q"].get("intent"), "reply": (r["q"].get("current_draft") or {}).get("reply"),
                   "citations": [(c["n"], c["url"]) for c in (r["q"].get("current_draft") or {}).get("citations", [])],
                   "routing": ((r["q"].get("current_draft") or {}).get("routing") or {}).get("note"),
                   "pattern": ((r["q"].get("current_draft") or {}).get("agents") or {}).get("pattern", {}).get("classification"),
                   "compliance_flags": ((r["q"].get("current_draft") or {}).get("agents") or {}).get("compliance", {}).get("flags"),
                   "seconds": r["q"].get("_seconds")} for k, r in results.items()}
    (out / "results.json").write_text(json.dumps({"summary": summary, "checks": ev.checks, "claims": claims, "queue_results": samples,
                                                  "isolation_diffs": iso, "refinement_rounds": refine_rounds, "cross_loop": cross,
                                                  "pulse_run_1": {k: run1.get(k) for k in ("id", "window_start", "window_end", "themes", "fee_confusion", "signals", "pulse", "explainer", "stats", "steps")}},
                                                 indent=2, ensure_ascii=False, default=str))
    # markdown report
    fails = [c for c in ev.checks if not c["pass"]]
    lines = [f"# Evaluation report — {ts}", "", f"Backend: `{args.base_url}`", "",
             f"**{summary['checks_passed']} / {summary['checks_total']} checks passed** · {len(real)} real review complaints · "
             f"{len(claims)} claims audited ({len(valid)} valid) · response-loop latency p50 {summary['latency_s']['p50']}s, max {summary['latency_s']['max']}s", ""]
    areas = sorted({c["area"] for c in ev.checks})
    lines += ["| Area | Passed | Total |", "|---|---|---|"]
    for a in areas:
        cs = [c for c in ev.checks if c["area"] == a]
        lines.append(f"| {a} | {sum(c['pass'] for c in cs)} | {len(cs)} |")
    lines += ["", "## Failures", ""] + ([f"- **{c['area']}** · {c['check']} — `{json.dumps(c['detail'], default=str)[:300]}`" for c in fails] or ["None."])
    lines += ["", "## Notes", ""] + [f"- {n}" for n in ev.notes]
    lines += ["", "## Claim audit (sample)", "", "| Loop | Claim | Valid | Evidence |", "|---|---|---|---|"]
    for c in claims[:40]:
        ev_ = ", ".join((c.get("sources") or c.get("evidence") or [])[:2])
        lines.append(f"| {c['loop']} | {c['claim'][:110].replace('|', '/')} | {'✅' if c['valid'] else '❌'} | {ev_[:120]} |")
    lines += ["", "## All checks", ""] + [f"- {'✅' if c['pass'] else '❌'} {c['area']} · {c['check']}" for c in ev.checks]
    report = "\n".join(lines)
    (out / "report.md").write_text(report)
    (ROOT / "evals" / "results" / "latest.md").write_text(report)
    print(f"\n{summary['checks_passed']}/{summary['checks_total']} checks passed -> {out}")


if __name__ == "__main__":
    main()
