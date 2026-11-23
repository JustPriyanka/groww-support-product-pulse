"""Groq client: JSON-mode calls with retry/backoff (pattern ported from the Zomato project).

Only ever called with redacted text. Callers validate every output in code.
"""
from __future__ import annotations

import json
import logging
import random
import re
import time

import threading
from collections import deque

import groq

from config import GROQ_API_KEY, GROQ_FAST_MODEL, GROQ_MODEL
from core.pii import contains_pii

log = logging.getLogger("llm")
_client: groq.Groq | None = None

MAX_RATE_LIMIT_RETRIES = 4


class LLMUnavailable(RuntimeError):
    pass


# Groq free tier: 8,000 tokens/minute per model. A client-side sliding-window limiter keeps
# us under it so parallel agents queue briefly instead of tripping 429s.
TPM_BUDGET = 7000
_usage: dict[str, deque] = {}
_ulock = threading.Lock()


def _reserve(model: str, est_tokens: int) -> list:
    """Block until the estimated tokens fit in the 60s window; returns the reservation slot."""
    while True:
        with _ulock:
            q = _usage.setdefault(model, deque())
            now = time.time()
            while q and now - q[0][0] > 60:
                q.popleft()
            used = sum(t[1] for t in q)
            if used + est_tokens <= TPM_BUDGET or not q:
                slot = [now, est_tokens]
                q.append(slot)
                return slot
            wait = 60 - (now - q[0][0]) + 0.2
        time.sleep(min(wait, 5))


def _settle(slot: list, actual: int | None) -> None:
    if actual:
        with _ulock:
            slot[1] = actual


def client() -> groq.Groq:
    global _client
    if not GROQ_API_KEY:
        raise LLMUnavailable("GROQ_API_KEY not configured")
    if _client is None:
        _client = groq.Groq(api_key=GROQ_API_KEY, timeout=60, max_retries=0)
    return _client


def _repair_json(raw: str) -> dict | None:
    for candidate in (raw, (re.search(r"\{.*\}", raw, re.S) or [None])[0]):
        if not candidate:
            continue
        for fix in (candidate, re.sub(r",\s*([}\]])", r"\1", candidate)):
            try:
                v = json.loads(fix)
                return v if isinstance(v, dict) else {"items": v}
            except json.JSONDecodeError:
                continue
    return None


def chat_json(system: str, user: str, *, fast: bool = False, temperature: float = 0.1,
              max_tokens: int = 2048, purpose: str = "") -> dict:
    """Call Groq expecting a JSON object. Raises LLMUnavailable after retries."""
    # Defence in depth: refuse to send PII to the provider.
    kinds = contains_pii(user)
    if kinds:
        raise ValueError(f"refusing to send PII ({kinds}) to LLM")
    model = GROQ_FAST_MODEL if fast else GROQ_MODEL
    slot = _reserve(model, int((len(system) + len(user)) / 3.2) + min(600, max_tokens // 3))
    attempt, timeouts = 0, 0
    while True:
        attempt += 1
        t0 = time.time()
        try:
            resp = client().chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                response_format={"type": "json_object"},
                reasoning_effort="low",
            )
            _settle(slot, getattr(getattr(resp, "usage", None), "total_tokens", None))
            raw = resp.choices[0].message.content or ""
            data = _repair_json(raw)
            log.info("llm ok purpose=%s model=%s ms=%d", purpose, model, int((time.time() - t0) * 1000))
            if data is None:
                if attempt <= 2:
                    continue
                raise LLMUnavailable("malformed JSON from model")
            return data
        except groq.RateLimitError:
            if attempt > MAX_RATE_LIMIT_RETRIES:
                raise LLMUnavailable("rate limited")
            wait = min(30, 2 ** attempt + random.random())
            log.warning("llm rate-limited purpose=%s wait=%.1fs", purpose, wait)
            time.sleep(wait)
        except groq.APITimeoutError:
            timeouts += 1
            if timeouts > 1:
                raise LLMUnavailable("timeout")
        except groq.BadRequestError as e:
            # JSON-mode validation failures surface as 400; retry once without temperature tweaks
            log.warning("llm bad request purpose=%s: %s", purpose, str(e)[:200])
            if attempt > 2:
                raise LLMUnavailable(f"bad request: {str(e)[:120]}")
        except groq.APIError as e:
            log.warning("llm api error purpose=%s: %s", purpose, str(e)[:200])
            if attempt > 2:
                raise LLMUnavailable("api error")
            time.sleep(1.5 * attempt)
