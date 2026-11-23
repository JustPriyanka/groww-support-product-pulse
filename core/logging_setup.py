"""Logging that cannot leak PII: every record is redacted before it is emitted.

Application code never logs question text in the first place (ids, intents and PII
*types* only); this filter is the second guard.
"""
import logging

from config import LOG_FILE, LOG_LEVEL
from core.pii import redact


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(str(record.msg)).text
        if isinstance(record.args, tuple):
            record.args = tuple(redact(a).text if isinstance(a, str) else a for a in record.args)
        return True


def setup_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_groww_configured", False):
        return
    root.setLevel(LOG_LEVEL)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for h in (logging.StreamHandler(), logging.FileHandler(LOG_FILE)):
        h.setFormatter(fmt)
        h.addFilter(RedactingFilter())
        root.addHandler(h)
    # uvicorn access logs include query strings; keep them but redacted
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(name)
        for h in lg.handlers:
            h.addFilter(RedactingFilter())
    root._groww_configured = True  # type: ignore[attr-defined]
