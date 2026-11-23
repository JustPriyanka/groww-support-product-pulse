"""
Pattern Agent — deterministic. Counts are facts about our own data, so no LLM is needed
(and none can invent a count).

Signals:
  - reviews with the same intent across the 12-week review window, last 4 weeks, weekly series
  - themes from the latest completed weekly pulse that contain matching reviews
  - questions with the same intent in the last 7 days vs the 7 days before
Classification:
  rising    : questions this week >= 3 and >= 2x previous week, OR reviews last 2 weeks >= 1.5x prior 2 weeks (min 5)
  recurring : questions this week >= 5, OR >= 8 matching reviews in the last 4 weeks of the window
  isolated  : otherwise
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agents.schemas import PatternOutput
from core import db
from core.reviews import all_reviews, dataset_window


def _question_counts(intent: str, now: datetime) -> tuple[int, int, dict]:
    start7 = now - timedelta(days=7)
    start14 = now - timedelta(days=14)
    q7 = db.one("SELECT COUNT(*) n FROM questions WHERE intent=? AND created_at>=?", intent, start7.isoformat(timespec="seconds"))["n"]
    qp = db.one("SELECT COUNT(*) n FROM questions WHERE intent=? AND created_at>=? AND created_at<?", intent,
                start14.isoformat(timespec="seconds"), start7.isoformat(timespec="seconds"))["n"]
    return q7, qp, {"start": start7.date().isoformat(), "end": now.date().isoformat(), "days": 7}


def run(intent: str, fee_type: str | None) -> PatternOutput:
    now = datetime.now(timezone.utc)
    w_start, w_end = dataset_window()
    q7, qp, qwin = _question_counts(intent, now)
    if intent in ("other", "voice_command_blocked"):
        return PatternOutput(intent=intent, classification="isolated" if q7 < 5 else "recurring", review_count=0,
                             review_window={"start": w_start.isoformat(), "end": w_end.isoformat()}, recent_review_count=0,
                             weekly_review_counts=[], sample_review_ids=[], matched_themes=[],
                             question_count_7d=q7, question_count_prev_7d=qp, question_window=qwin,
                             rationale="question did not match a known intent; review matching skipped")

    matches = [r for r in all_reviews() if r.intent == intent and r.words >= 4]
    weekly = []
    for i in range(12):
        we = w_end - timedelta(days=7 * i)
        ws = we - timedelta(days=6)
        weekly.append({"week_start": ws.isoformat(), "week_end": we.isoformat(),
                       "count": sum(1 for r in matches if ws <= r.date <= we)})
    weekly.reverse()
    last4 = sum(w["count"] for w in weekly[-4:])
    last2, prev2 = sum(w["count"] for w in weekly[-2:]), sum(w["count"] for w in weekly[-4:-2])

    # themes from latest completed pulse run
    themes = []
    run_row = db.one("SELECT id, themes, window_start, window_end FROM pulse_runs WHERE status='completed' ORDER BY id DESC LIMIT 1")
    if run_row and isinstance(run_row.get("themes"), dict):
        ids = {r.review_id for r in matches}
        for t in run_row["themes"].get("themes", []):
            overlap = [rid for rid in t.get("review_ids", []) if rid in ids]
            if overlap:
                themes.append({"theme": t["name"], "matching_reviews": len(overlap), "theme_count": t["count"],
                               "pulse_run_id": run_row["id"], "window": {"start": run_row["window_start"], "end": run_row["window_end"]}})

    reasons = []
    if (q7 >= 3 and q7 >= 2 * max(qp, 1)) or (last2 >= 5 and last2 >= 1.5 * max(prev2, 1)):
        cls = "rising"
        reasons.append(f"questions {q7} this week vs {qp} previous; reviews {last2} in last 2 weeks vs {prev2} in prior 2")
    elif q7 >= 5 or last4 >= 8:
        cls = "recurring"
        reasons.append(f"{q7} questions in 7 days; {last4} matching reviews in the last 4 weeks of the review window")
    else:
        cls = "isolated"
        reasons.append(f"only {q7} questions in 7 days and {last4} matching reviews in the last 4 weeks")
    sample = [r.review_id for r in sorted(matches, key=lambda r: r.date, reverse=True)[:5]]
    return PatternOutput(intent=intent, classification=cls, review_count=len(matches),
                         review_window={"start": w_start.isoformat(), "end": w_end.isoformat()},
                         recent_review_count=last4, weekly_review_counts=weekly, sample_review_ids=sample,
                         matched_themes=themes, question_count_7d=q7, question_count_prev_7d=qp,
                         question_window=qwin, rationale="; ".join(reasons))
