"""De-identified review dataset access (committed snapshot + optional live refresh)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

from config import REVIEWS_CSV, REVIEWS_LIVE_CSV
from core.intents import classify


@dataclass(frozen=True)
class Review:
    review_id: str
    date: date
    rating: int
    text: str
    source_url: str
    intent: str
    fee_type: str | None

    @property
    def words(self) -> int:
        return len(self.text.split())


def _load(path) -> list[Review]:
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = classify(r["text"])
            out.append(Review(r["review_id"], date.fromisoformat(r["review_date"]), int(r["rating"]),
                              r["text"], r["source_url"], c.intent, c.fee_type))
    return out


@lru_cache(maxsize=1)
def _cached(path: str, mtime: float) -> tuple[Review, ...]:
    return tuple(_load(path))


def all_reviews() -> tuple[Review, ...]:
    path = REVIEWS_LIVE_CSV if REVIEWS_LIVE_CSV.exists() else REVIEWS_CSV
    return _cached(str(path), path.stat().st_mtime)


def by_id() -> dict[str, Review]:
    return {r.review_id: r for r in all_reviews()}


def latest_date() -> date:
    return max(r.date for r in all_reviews())


def window(end: date, days: int) -> tuple[date, date]:
    return end - timedelta(days=days - 1), end


def in_window(start: date, end: date, substantive_only: bool = False, min_words: int = 6) -> list[Review]:
    return [r for r in all_reviews() if start <= r.date <= end and (not substantive_only or r.words >= min_words)]


def dataset_window() -> tuple[date, date]:
    ds = [r.date for r in all_reviews()]
    return min(ds), max(ds)
