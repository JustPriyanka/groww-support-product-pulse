"""
Fetch the official source list and build data/corpus/{sources.json, docs/<id>.txt}.

Input:  data/corpus/source_list.json  [{id, url, publisher, title, topics}]
Output: data/corpus/sources.json      (+ type, fetched_at = "Last checked", sha256, chars)
        data/corpus/docs/<id>.txt     (extracted, PII-redacted text)

Downloaded bytes are treated as untrusted data: parsed only, never executed.

Usage: python -I scripts/build_corpus.py [--only id1,id2]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.pii import redact  # noqa: E402

CORPUS = ROOT / "data" / "corpus"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept-Language": "en-IN,en;q=0.9"}
ALLOWED_DOMAINS = ("hdfcfund.com", "sebi.gov.in", "amfiindia.com", "mutualfundssahihai.com", "groww.in")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Next.js pages: server-rendered text is in the DOM; drop chrome
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form", "iframe"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    BLOCK = ["h1", "h2", "h3", "h4", "h5", "p", "li", "ul", "ol", "tr", "table", "div", "section", "br", "dt", "dd"]
    for el in main.find_all(BLOCK):
        el.insert_before("\n\n" + ("- " if el.name == "li" else ""))
        el.insert_after("\n\n")
    raw = main.get_text("")
    paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", raw)]
    paras = [p for p in paras if len(p) >= 3 and p != "-"]
    out, prev = [], None
    for b in paras:
        if b != prev:
            out.append(b)
        prev = b
    # cut site-wide footer / navigation boilerplate (Groww pages)
    for marker in ("Was the answer helpful?", "Vaishnavi Tech Park", "© 2016-"):
        idx = next((i for i, b in enumerate(out) if b.startswith(marker) or marker in b[:40]), None)
        if idx is not None:
            out = out[:idx]
    return "\n\n".join(out)


def pdf_to_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for p in reader.pages[:60]:
        t = p.extract_text() or ""
        pages.append(t)
    text = "\n".join(pages)
    text = re.sub(r"-\n(?=[a-z])", "", text)
    # join hard-wrapped lines inside paragraphs
    text = re.sub(r"(?<![.\n:])\n(?!\n|[-•*●]\s|\d+\.)", " ", text)
    return re.sub(r"[ \t]+", " ", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = set(filter(None, args.only.split(",")))
    items = json.loads((CORPUS / "source_list.json").read_text())
    existing = {m["id"]: m for m in json.loads((CORPUS / "sources.json").read_text())} if (CORPUS / "sources.json").exists() else {}
    (CORPUS / "docs").mkdir(parents=True, exist_ok=True)
    out = []
    for it in items:
        if only and it["id"] not in only and it["id"] in existing:
            out.append(existing[it["id"]])
            continue
        host = re.sub(r"^https?://", "", it["url"]).split("/")[0]
        if not any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS):
            print(f"SKIP {it['id']}: {host} is not an allowed official domain")
            continue
        try:
            r = requests.get(it["url"], headers=UA, timeout=45)
            r.raise_for_status()
        except Exception as e:
            print(f"FAIL {it['id']}: {e}")
            if it["id"] in existing:
                out.append(existing[it["id"]])
            continue
        is_pdf = "pdf" in r.headers.get("content-type", "") or r.content[:4] == b"%PDF"
        text = pdf_to_text(r.content) if is_pdf else html_to_text(r.text)
        red = redact(text)  # strips helpline numbers / emails so they can't leak into drafts
        text = red.text.strip()
        if len(text) < 300:
            print(f"WARN {it['id']}: only {len(text)} chars extracted (JS-rendered?)")
        (CORPUS / "docs" / f"{it['id']}.txt").write_text(text, encoding="utf-8")
        meta = {**it, "type": "pdf" if is_pdf else "html",
                "fetched_at": datetime.now(timezone.utc).date().isoformat(),
                "sha256": hashlib.sha256(text.encode()).hexdigest(), "chars": len(text),
                "pii_redacted": red.found}
        out.append(meta)
        print(f"OK   {it['id']:<28} {meta['type']:<4} {len(text):>7} chars  redacted={red.found}")
    (CORPUS / "sources.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"{len(out)} sources")


if __name__ == "__main__":
    main()
