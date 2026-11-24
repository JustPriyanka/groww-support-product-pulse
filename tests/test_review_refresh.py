"""Weekly review refresh must accumulate: a later refresh may not drop reviews an earlier one added."""
import csv
from datetime import date, datetime, timezone

import config
import scripts.collect_reviews as cr


def _play(rid: str, day: int) -> dict:
    return {"reviewId": rid, "at": datetime(2026, 11, day, 12, tzinfo=timezone.utc), "content": f"review {rid} text",
            "score": 4, "thumbsUpCount": 0, "reviewCreatedVersion": "1.0"}


def _ids(path) -> set[str]:
    with open(path, encoding="utf-8") as f:
        return {r["review_id"] for r in csv.DictReader(f)}


def test_second_refresh_keeps_reviews_from_first(tmp_path, monkeypatch):
    snap, live = tmp_path / "snap.csv", tmp_path / "live.csv"
    with snap.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cr.FIELDS)
        w.writeheader()
        w.writerow({k: "" for k in cr.FIELDS} | {"review_id": "GP-snap", "review_date": "2026-11-22", "rating": 5, "text": "old"})
    monkeypatch.setattr(config, "REVIEWS_CSV", snap)
    monkeypatch.setattr(config, "REVIEWS_LIVE_CSV", live)

    store = [_play("a", 23)]
    monkeypatch.setattr(cr, "reviews", lambda *a, **k: (list(store), None))
    first = cr.fetch_new(since=date(2026, 11, 23))
    day23 = cr.stable_id("a")
    assert first["new_reviews"] == 1 and day23 in _ids(live)

    store[:] = [_play("b", 24), _play("a", 23)]
    cr.fetch_new(since=date(2026, 11, 24))
    assert {"GP-snap", day23, cr.stable_id("b")} <= _ids(live)

    cr.fetch_new(since=date(2026, 11, 24))  # re-fetching the same day must not duplicate rows
    with open(live, encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 3
