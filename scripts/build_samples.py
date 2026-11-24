"""Build the submission samples in samples/ from a running backend (local or deployed).

    .venv/bin/python scripts/build_samples.py --base-url https://<railway-domain> [--skip-questions]

Writes:
  samples/reviews_sample.csv      de-identified review rows from the latest pulse window
  samples/sample_questions.md     five questions through the response loop (draft, citations, routing, review)
  samples/reviewer_rejection.md   one corrected draft and one blocked draft (needs ENABLE_EVAL_HOOKS=true)
  samples/weekly_pulse.md         latest weekly pulse, themes, fee confusion, fee explainer, pending actions
  samples/workspace.md            appended document entries and email drafts, as stored by the MCP server
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples"

QUESTIONS = [
    ("Fee question, covered by official sources",
     "Why was a DP charge deducted when I sold my shares?"),
    ("Scheme-specific question (answer must come from that fund's own KIM)",
     "Is there an exit load on HDFC Mid Cap Fund if I redeem within a year?"),
    ("Investment advice request (factual part only, no recommendation)",
     "Should I buy HDFC Small Cap Fund now or wait for a correction?"),
    ("Performance request (no return figures)",
     "What returns did HDFC Mid Cap Fund give in the last 3 years?"),
    ("Not covered by the corpus, with PII in the question (redacted, said out loud, escalated)",
     "My PAN is ABCDE1234F. How is tax deducted on dividends from US stocks?"),
]


def q_block(title: str, q: dict) -> str:
    d = q.get("current_draft") or {}
    r = d.get("routing") or {}
    lines = [f"## {title}", "",
             f"**Question (as stored, after redaction):** {q['text_redacted']}", "",
             f"- intent `{q['intent']}` · fee type `{q.get('fee_type')}` · scheme `{q.get('scheme')}` · PII types {q.get('pii_types') or []}",
             f"- status **{q['status']}** · draft origin `{d.get('origin')}` · reviewer {'passed' if d.get('passed') else 'FAILED'}"
             + (f" · flags {[f['code'] for f in (d.get('review') or {}).get('flags', [])]}" if not d.get("passed") else ""),
             "", "**Draft reply**", "", "> " + (d.get("reply") or "").replace("\n", "\n> "), ""]
    for c in d.get("citations") or []:
        lines.append(f"[{c['n']}] {c['publisher']} — {c['title']} — {c['url']}")
        for qt in c.get("quotes", [])[:2]:
            lines.append(f"    · cited text: “{qt[:220]}”")
    lines += ["", f"Last checked: {d.get('last_checked')}", "",
              f"**Routing:** {r.get('team')} (+{', '.join(r.get('also_notify') or []) or '—'}), {r.get('priority')}"]
    lines += [f"- {x}" for x in (r.get("disagreements") or []) + (r.get("reasons") or [])]
    agents = {a["agent"]: a for a in q.get("agent_runs") or []}
    if agents:
        lines += ["", "**Agent runs:** " + ", ".join(f"{k} {v.get('status')} ({v.get('duration_ms')} ms)" for k, v in agents.items())]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--skip-questions", action="store_true")
    args = ap.parse_args()
    c = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=300)
    OUT.mkdir(exist_ok=True)

    run = c.get("/api/pulse/latest").json()
    run = run.get("run", run)

    if not args.skip_questions:
        parts = ["# Five sample questions through the response loop", "",
                 f"Generated against `{args.base_url}` by `scripts/build_samples.py`.", ""]
        for title, text in QUESTIONS:
            q = c.post("/api/questions", json={"text": text, "channel": "typed"}).json()
            parts.append(q_block(title, q))
            print("asked:", text[:60], "->", q.get("status"))
        (OUT / "sample_questions.md").write_text("\n".join(parts), encoding="utf-8")

        rej = ["# Reviewer rejection", ""]
        # 1. A human edit that adds advice, a return promise and an uncited claim. Every edit is
        #    re-reviewed by the same code rules; a failing edit is refused and the draft is unchanged.
        q = c.post("/api/questions", json={"text": "Are DP charges charged per stock or per order?", "channel": "typed"}).json()
        d = q["current_draft"]
        bad = (d["reply"].split("[1]")[0] + "[1]. You should switch to HDFC Mid Cap Fund instead, "
               "it will earn you 18% a year. Groww is the cheapest broker in India.")
        r = c.post(f"/api/drafts/{d['id']}/edit", json={"reply": bad})
        body = r.json()
        flags = ((body.get("detail") or {}).get("flags") if isinstance(body.get("detail"), dict) else body.get("flags")) or []
        after = c.get(f"/api/questions/{q['id']}").json()
        rej += ["## Human edit rejected by the reviewer", "",
                f"**Question:** {q['text_redacted']}", "", "**Passing draft**", "", "> " + d["reply"], "",
                "**Edit submitted by a support agent**", "", "> " + bad, "",
                f"**Result:** HTTP {r.status_code} — `{json.dumps(body, ensure_ascii=False)[:200]}`", ""]
        rej += [f"- `{f['code']}` — {f['detail']}" + (f" — “{f['sentence']}”" if f.get("sentence") else "") for f in flags]
        rej += ["", f"Current draft after the refused edit is still #{after['current_draft_id']} "
                f"(unchanged: {after['current_draft_id'] == d['id']}).", ""]
        # 2. Injected faults (eval-only X-Eval-Fault header; needs ENABLE_EVAL_HOOKS=true on the backend)
        for title, text, fault in [
                ("Injected uncited claim → one named correction → passes", "Are DP charges charged per stock or per order?", "uncited"),
                ("Uncited claim twice → blocked, approval refused", "Is GST added on top of DP charges when I sell?", "uncited_twice")]:
            q = c.post("/api/questions", json={"text": text, "channel": "eval"}, headers={"X-Eval-Fault": fault}).json()
            if (q.get("drafts") or [{}])[0].get("passed"):
                rej += [f"_Fault-injection demo “{title}” skipped: ENABLE_EVAL_HOOKS is off on this backend._", ""]
                continue
            rej += [f"## {title}", "", f"**Question:** {q.get('text_redacted')}", f"**Final status:** {q.get('status')}", ""]
            for d in q.get("drafts", []):
                flags = [f"{f['code']}: {f['detail']}" for f in (d.get("review") or {}).get("flags", [])]
                rej += [f"### Draft attempt {d['attempt']} (`{d['origin']}`{', ' + d['correction_name'] if d.get('correction_name') else ''})",
                        "", "> " + d["reply"], "", f"Reviewer: {'passed' if d['passed'] else 'FAILED'}"]
                rej += [f"- {f}" for f in flags] + [""]
            if q.get("status") == "blocked":
                r = c.post(f"/api/drafts/{q['current_draft_id']}/approve")
                rej += [f"Approve attempt on the blocked draft → HTTP {r.status_code}: `{r.text[:160]}`", ""]
        (OUT / "reviewer_rejection.md").write_text("\n".join(rej), encoding="utf-8")

    # weekly pulse
    ex = (run.get("explainer") or {}).get("draft") or {}
    conf = run.get("fee_confusion") or {}
    pulse = ["# Weekly product pulse (latest run)", "",
             f"Run {run['id']} · trigger `{run['trigger']}` · window {run['window_start']} → {run['window_end']} · status {run['status']}", "",
             "## Pulse (as appended to the “Weekly Product Pulse” document on approval)", "",
             (run.get("pulse") or {}).get("markdown", ""), "",
             f"_{(run.get('pulse') or {}).get('words')} words; reviewer: {'passed' if ((run.get('pulse') or {}).get('review') or {}).get('passed') else 'FAILED'}_", "",
             "## Themes (every review ID resolves to a real review in the window)", ""]
    for t in (run.get("themes") or {}).get("themes", []):
        pulse.append(f"- **{t['name']}** — {t['count']} reviews, avg ★{t.get('avg_rating')} — e.g. {', '.join(t['review_ids'][:4])}")
    pulse += ["", "## Fee issue found in the reviews", "",
              f"**{conf.get('fee_type')}** — {conf.get('statement')} ({conf.get('count')} reviews, "
              f"{(conf.get('window') or {}).get('start')} → {(conf.get('window') or {}).get('end')}; e.g. {', '.join((conf.get('review_ids') or [])[:5])})",
              "", "## Fee explainer (drafted from official sources)", "", ex.get("markdown", "—"), "",
              "## Pending actions created by this run (each approved separately)", ""]
    for a in run.get("actions") or []:
        pulse.append(f"- #{a['id']} `{a['kind']}` → {a['target']} — **{a['status']}**")
    pulse += ["", "## Run steps", ""] + [f"- {s['step']}: {s['status']}" for s in run.get("steps") or []]
    (OUT / "weekly_pulse.md").write_text("\n".join(pulse) + "\n", encoding="utf-8")

    # workspace (written only by the MCP server, after approval)
    ws = c.get("/api/workspace").json()
    w = ["# Workspace written by the MCP server (after human approval)", "",
         "The backend never writes these; each entry carries the approved action id and the payload hash the approver saw.", ""]
    for doc in ws["contents"].values():
        w += [f"## Document: {doc['title']} ({len(doc['entries'])} entries)", ""]
        for e in doc["entries"][-1:]:
            w += [f"### Entry {e['id']} — action #{e['action_id']} — {e['created_at']}", f"payload sha256 `{e['payload_sha256']}`", "", e["body"], ""]
    w += ["## Email drafts (stored as drafts; no send tool exists)", ""]
    for e in ws.get("email_drafts", [])[-1:]:
        w += [f"### Draft {e.get('id')} — action #{e.get('action_id')} — status `{e.get('status')}`",
              f"**To:** {e.get('to_label')}  ", f"**Subject:** {e.get('subject')}", "", e.get("body", ""), ""]
    if not ws.get("email_drafts"):
        w.append("_No email draft approved yet — approve the pulse's `email_draft` action in Approvals._")
    (OUT / "workspace.md").write_text("\n".join(w) + "\n", encoding="utf-8")

    # reviews sample: real rows from the latest window, theme examples first
    ids = [rid for t in (run.get("themes") or {}).get("themes", []) for rid in t["review_ids"][:6]]
    ids += [rid for rid in conf.get("review_ids", []) if rid not in ids]
    rows = c.get("/api/reviews", params={"ids": ",".join(ids[:40])}).json()["reviews"]
    with (OUT / "reviews_sample.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["review_id", "date", "rating", "intent", "text", "source_url"])
        wr.writeheader()
        wr.writerows({k: r[k] for k in wr.fieldnames} for r in rows)
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
