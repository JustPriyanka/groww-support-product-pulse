"""
Official-source corpus: sentence-level IDs + BM25 retrieval.

Only sentence IDs produced here can be cited. A citation that does not resolve to one
of these IDs is invalid (reviewer: UNCITED_CLAIM).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache

from rank_bm25 import BM25Okapi

from config import CORPUS_DIR
from core.policy import split_sentences

_TOKEN = re.compile(r"[a-z0-9₹%.]+")
_STOP = set("a an the of to in on for and or is are was be by with as at from this that it its your you we our i my me can will do does what how why when which who any per".split())

# Query expansion for domain vocabulary (users say "dp fee", sources say "depository participant charges")
SYNONYMS = {
    "dp": ["depository", "participant", "dp"],
    "depository": ["dp", "depository"],
    "sell": ["sell", "selling", "debit", "sold"],
    "selling": ["sell", "selling", "debit"],
    "charge": ["charge", "charges", "fee", "fees"],
    "charges": ["charge", "charges", "fee", "fees"],
    "fee": ["fee", "fees", "charge", "charges"],
    "hidden": ["charges", "statutory", "brokerage", "gst", "stt"],
    "gst": ["gst", "goods", "services", "tax"],
    "brokerage": ["brokerage", "order", "₹20", "0.1%"],
    "exit": ["exit", "load", "redeemed", "redemption", "switched"],
    "redeem": ["redeem", "redemption", "redeemed", "exit", "load"],
    "expense": ["expense", "ratio", "ter", "recurring"],
    "ter": ["total", "expense", "ratio"],
    "mtf": ["mtf", "margin", "trading", "facility", "interest"],
    "stamp": ["stamp", "duty", "0.005%"],
    "sip": ["sip", "systematic", "investment", "plan", "instalment"],
    "nav": ["nav", "net", "asset", "value"],
    "withdraw": ["withdraw", "withdrawal", "payout", "bank"],
}


def tokenize(text: str, expand: bool = False) -> list[str]:
    toks = [t.strip(".") for t in _TOKEN.findall(text.lower())]
    toks = [t for t in toks if t and t not in _STOP]
    if expand:
        extra = [s for t in toks for s in SYNONYMS.get(t, [])]
        toks = toks + extra
    return toks


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    publisher: str
    title: str
    type: str
    fetched_at: str
    sha256: str
    topics: tuple[str, ...]


@dataclass(frozen=True)
class Sentence:
    sid: str          # "<source_id>#s<n>"
    source_id: str
    text: str
    heading: bool = False   # page heading / nav label: context only, never citable
    section: str = ""       # nearest heading above this sentence
    lead_sid: str = ""      # for bullets: the "...:" sentence the list hangs off

    @property
    def citable(self) -> bool:
        return not self.heading

    def context_text(self) -> str:
        """Text shown to the LLM: section heading as a prefix so a row like
        "0.10% with min ₹100" under "NRI brokerage charges" is not read as a general rule."""
        return f"[{self.section}] {self.text}" if self.section else self.text


_BULLET = re.compile(r"^[-•*]\s")


def _is_heading(para: str) -> bool:
    """Short single-line paragraph without sentence punctuation (headings, nav labels).
    Question headings ("What are DP charges?") count; numeric rows do not."""
    if _BULLET.match(para) or len(split_sentences(para)) != 1 or len(para.split()) > 12:
        return False
    if para.endswith((".", ":", ";", ",")):
        return False
    return not (re.search(r"\d", para) and not para.endswith("?"))


@dataclass(frozen=True)
class Chunk:
    cid: str
    source_id: str
    sentence_ids: tuple[str, ...]
    text: str


class Corpus:
    def __init__(self) -> None:
        meta = json.loads((CORPUS_DIR / "sources.json").read_text())
        self.sources: dict[str, Source] = {
            m["id"]: Source(m["id"], m["url"], m["publisher"], m["title"], m["type"], m["fetched_at"],
                            m["sha256"], tuple(m.get("topics", []))) for m in meta}
        self.sentences: dict[str, Sentence] = {}
        self.chunks: list[Chunk] = []
        for sid in self.sources:
            text = (CORPUS_DIR / "docs" / f"{sid}.txt").read_text(encoding="utf-8")
            sents: list[Sentence] = []
            n = 0
            section, lead = "", ""
            for para in re.split(r"\n\s*\n|\n(?=[-•*]\s)", text):
                para = " ".join(para.split())
                if not para:
                    continue
                heading = _is_heading(para)
                bullet = bool(_BULLET.match(para))
                if not bullet:
                    lead = ""
                for s in split_sentences(para):
                    if len(s) < 12:
                        continue
                    n += 1
                    sents.append(Sentence(f"{sid}#s{n}", sid, s, heading=heading,
                                          section="" if heading else section,
                                          lead_sid=lead if bullet else ""))
                    if s.endswith(":") and not heading:
                        lead = f"{sid}#s{n}"   # following bullets hang off this sentence
                if heading:
                    section, lead = para, ""
            for s in sents:
                self.sentences[s.sid] = s
            # ~120-word chunks with 1-sentence overlap
            buf: list[Sentence] = []
            words = 0
            for s in sents:
                buf.append(s)
                words += len(s.text.split())
                if words >= 120:
                    self._add_chunk(sid, buf)
                    buf, words = buf[-1:], len(buf[-1].text.split())
            if buf:
                self._add_chunk(sid, buf)
        title_of = {s: self.sources[s].title for s in self.sources}
        self._bm25 = BM25Okapi([tokenize(title_of[c.source_id] + " " + c.text) for c in self.chunks])
        self._sids = list(self.sentences)
        # heading sentences are context only: keep them out of sentence-level retrieval
        self._sids = [i for i in self._sids if self.sentences[i].citable]
        self._bm25_s = BM25Okapi([tokenize(title_of[self.sentences[i].source_id] + " " + self.sentences[i].context_text())
                                  for i in self._sids])

    def _add_chunk(self, sid: str, buf: list[Sentence]) -> None:
        self.chunks.append(Chunk(f"{sid}#c{len(self.chunks)}", sid, tuple(s.sid for s in buf), " ".join(s.text for s in buf)))

    def search(self, query: str, k: int = 6, source_filter: set[str] | None = None) -> list[tuple[Chunk, float]]:
        q = tokenize(query, expand=True)
        if not q:
            return []
        scores = self._bm25.get_scores(q)
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        out = []
        for i in ranked:
            c = self.chunks[i]
            if source_filter and c.source_id not in source_filter:
                continue
            if scores[i] <= 0:
                break
            out.append((c, float(scores[i])))
            if len(out) >= k:
                break
        return out

    def search_sentences(self, query: str, k: int = 12, source_filter: set[str] | None = None) -> list[tuple[str, float]]:
        q = tokenize(query, expand=True)
        if not q:
            return []
        scores = self._bm25_s.get_scores(q)
        ranked = sorted(range(len(self._sids)), key=lambda i: scores[i], reverse=True)
        out = []
        for i in ranked:
            sid = self._sids[i]
            if scores[i] <= 0:
                break
            if source_filter and self.sentences[sid].source_id not in source_filter:
                continue
            out.append((sid, float(scores[i])))
            if len(out) >= k:
                break
        return out

    def resolve(self, sentence_id: str) -> Sentence | None:
        return self.sentences.get(sentence_id)

    def source_of(self, sentence_id: str) -> Source | None:
        s = self.sentences.get(sentence_id)
        return self.sources.get(s.source_id) if s else None


@lru_cache(maxsize=1)
def get_corpus() -> Corpus:
    return Corpus()
