"""
Collect REAL public Groww reviews from Google Play for a recent window and save a
de-identified CSV.

Privacy: reviews are redacted in memory with core.pii.redact BEFORE anything is written.
Author names, avatars, and developer replies are never written to disk.

Usage:
    python scripts/collect_reviews.py --start 2026-08-31 --end 2026-11-23
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.pii import redact  # noqa: E402

APP_ID = "com.nextbillion.groww"
APP_URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=en_IN"
OUT = ROOT / "data" / "reviews" / "groww_reviews.csv"
FIELDS = [
    "review_id", "play_review_id", "source", "source_url", "review_date", "rating", "text",
    "thumbs_up", "app_version", "pii_redacted", "collected_at",
]


def stable_id(play_review_id: str) -> str:
    """Short, stable, non-reversible id derived from the public Play review id."""
    return "GP-" + hashlib.sha256(play_review_id.encode()).hexdigest()[:10]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--max", type=int, default=20000)
    args = ap.parse_args()
    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc).replace(hour=23, minute=59)

    rows, token, fetched = [], None, 0
    collected_at = datetime.now(timezone.utc).date().isoformat()
    while fetched < args.max:
        batch, token = reviews(APP_ID, lang="en", country="in", sort=Sort.NEWEST,
                               count=200, continuation_token=token)
        if not batch:
            break
        fetched += len(batch)
        oldest = None
        for r in batch:
            at = r["at"].replace(tzinfo=timezone.utc)
            oldest = at
            if not (start <= at <= end):
                continue
            content = (r.get("content") or "").strip()
            if not content:
                continue
            red = redact(content)
            rows.append({
                "review_id": stable_id(r["reviewId"]),
                "play_review_id": r["reviewId"],
                "source": "google_play",
                # Public Play listing deep-linked to the review id (provenance).
                "source_url": f"{APP_URL}&reviewId={r['reviewId']}",
                "review_date": at.date().isoformat(),
                "rating": r["score"],
                "text": red.text,
                "thumbs_up": r.get("thumbsUpCount", 0),
                "app_version": r.get("reviewCreatedVersion") or "",
                "pii_redacted": "|".join(red.found),
                "collected_at": collected_at,
            })
        print(f"fetched={fetched} kept={len(rows)} oldest_in_batch={oldest}", file=sys.stderr)
        if oldest and oldest < start:
            break
        if token is None:
            break

    # de-duplicate on review_id
    seen, uniq = set(), []
    for r in rows:
        if r["review_id"] not in seen:
            seen.add(r["review_id"])
            uniq.append(r)
    uniq.sort(key=lambda r: r["review_date"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(uniq)
    print(f"wrote {len(uniq)} reviews -> {OUT}")


if __name__ == "__main__":
    main()


def fetch_new(since, max_fetch: int = 3000) -> dict:
    """Weekly-loop refresh: fetch reviews newer than `since`, redact, and write a merged copy
    (committed snapshot + new) to DATA_DIR. Network failures propagate to the caller, which
    falls back to the snapshot."""
    from config import REVIEWS_CSV, REVIEWS_LIVE_CSV
    start = datetime(since.year, since.month, since.day, tzinfo=timezone.utc)
    collected_at = datetime.now(timezone.utc).date().isoformat()
    new, token, fetched = [], None, 0
    while fetched < max_fetch:
        batch, token = reviews(APP_ID, lang="en", country="in", sort=Sort.NEWEST, count=200, continuation_token=token)
        if not batch:
            break
        fetched += len(batch)
        oldest = None
        for r in batch:
            at = r["at"].replace(tzinfo=timezone.utc)
            oldest = at
            content = (r.get("content") or "").strip()
            if at < start or not content:
                continue
            red = redact(content)
            new.append({"review_id": stable_id(r["reviewId"]), "play_review_id": r["reviewId"], "source": "google_play",
                        "source_url": f"{APP_URL}&reviewId={r['reviewId']}", "review_date": at.date().isoformat(),
                        "rating": r["score"], "text": red.text, "thumbs_up": r.get("thumbsUpCount", 0),
                        "app_version": r.get("reviewCreatedVersion") or "", "pii_redacted": "|".join(red.found),
                        "collected_at": collected_at})
        if (oldest and oldest < start) or token is None:
            break
    with open(REVIEWS_CSV, encoding="utf-8") as f:
        base = list(csv.DictReader(f))
    seen = {r["review_id"] for r in base}
    added = [r for r in new if r["review_id"] not in seen]
    rows = sorted(base + added, key=lambda r: r["review_date"], reverse=True)
    tmp = REVIEWS_LIVE_CSV.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(REVIEWS_LIVE_CSV)
    return {"fetched": fetched, "new_reviews": len(added), "since": since.isoformat(), "total": len(rows)}
