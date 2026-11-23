"""Structured outputs exchanged between agents (validated with Pydantic)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Fact(BaseModel):
    claim: str
    sentence_ids: list[str] = Field(min_length=1)
    source_id: str
    url: str
    title: str
    publisher: str
    quotes: list[str] = []
    last_checked: str


class FactsOutput(BaseModel):
    agent: Literal["facts"] = "facts"
    status: Literal["covered", "not_covered"]
    facts: list[Fact] = []
    searched: dict  # {query_terms, sources_considered, top_chunks, scheme_filter}
    topic: str
    mode: Literal["llm", "extractive"] = "llm"
    note: str = ""


class PatternOutput(BaseModel):
    agent: Literal["pattern"] = "pattern"
    intent: str
    classification: Literal["recurring", "rising", "isolated"]
    review_count: int
    review_window: dict          # {start, end}
    recent_review_count: int     # last 4 weeks of the review window
    weekly_review_counts: list[dict]
    sample_review_ids: list[str]
    matched_themes: list[dict]
    question_count_7d: int
    question_count_prev_7d: int
    question_window: dict
    rationale: str


class ComplianceOutput(BaseModel):
    agent: Literal["compliance"] = "compliance"
    pii_types: list[str] = []
    advice_request: bool = False
    performance_request: bool = False
    flags: list[str] = []
    llm_flags: list[str] = []
    llm_used: bool = False
    allowed_scope: str = "facts_only"


class Citation(BaseModel):
    n: int
    source_id: str
    url: str
    title: str
    publisher: str
    sentence_ids: list[str]
    quotes: list[str]
    last_checked: str


class Routing(BaseModel):
    team: str
    also_notify: list[str] = []
    priority: Literal["P1", "P2", "P3"]
    reasons: list[str]
    disagreements: list[str] = []
    note: str


class ReviewFlag(BaseModel):
    code: str
    detail: str
    sentence: str | None = None


class ReviewResult(BaseModel):
    passed: bool
    flags: list[ReviewFlag] = []
    checks: dict = {}
