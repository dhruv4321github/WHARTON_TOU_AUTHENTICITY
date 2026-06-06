"""
Extract clean text from an EDGAR filing (proxy statements are HTML; a few legacy
filings are plain-text SGML).

Proxies are long HTML documents with heavy executive-compensation tables. We keep
all readable text (numbers in tables don't match the value lexicons, so they add
little noise to the emphasis vector) and only strip non-content tags. Returns the
(text, n_pages, status) contract the miner expects.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

log = logging.getLogger("part2.extract_filing")

# Proxies run tens of thousands of words; anything tiny is a stub/error page.
_MIN_TEXT_CHARS = 2000
_STRIP = ("script", "style", "head", "title", "meta", "link", "noscript")
# Rough chars-per-page so the n_pages column stays meaningful for HTML filings.
_CHARS_PER_PAGE = 3000


def extract_text(path: str) -> tuple[str, int, str]:
    """Return (clean_text, approx_pages, status).

    status ∈ {"ok", "scanned_or_empty", "extract_failed"} — same vocabulary as the
    PDF extractor so coverage reporting is uniform across document types.
    """
    try:
        raw = open(path, "rb").read()
    except OSError as exc:
        log.warning("read failed %s: %s", path, exc)
        return "", 0, "extract_failed"

    text = raw.decode("utf-8", errors="ignore")
    head = text[:5000].lower()
    if "<html" in head or "<table" in head or "<div" in head or "<p" in head:
        soup = BeautifulSoup(text, "lxml")
        for tag in soup(list(_STRIP)):
            tag.decompose()
        body = soup.get_text(separator=" ")
    else:
        body = text  # legacy plain-text filing

    clean = re.sub(r"\s+", " ", body).strip()
    n_pages = max(1, len(clean) // _CHARS_PER_PAGE)
    if len(clean) < _MIN_TEXT_CHARS:
        return clean, n_pages, "scanned_or_empty"
    return clean, n_pages, "ok"
