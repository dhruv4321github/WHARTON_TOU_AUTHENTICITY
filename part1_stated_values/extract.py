"""
Fetching archived HTML and turning it into clean, comparable body text.

Pipeline per snapshot:
    raw_url -> fetch_html() -> extract_clean_text() -> normalize_for_compare()
and across years:
    text_changed() compares consecutive cleaned texts.

Design notes
------------
* Extraction uses trafilatura as the primary engine (it is purpose-built for
  stripping nav/footer/boilerplate and is robust to the messy, decade-old markup
  the Wayback Machine serves). A BeautifulSoup fallback handles the cases where
  trafilatura returns nothing.
* Change detection is deliberately KEPT OUT of the LLM. Whether a page changed
  is a deterministic, cheap, reproducible question; we answer it with text
  hashing + a similarity ratio and reserve the LLM for the interpretive
  questions (themes, linguistic shifts). This also makes the LLM step cheaper.
"""

from __future__ import annotations

import hashlib
import logging
import re
from difflib import SequenceMatcher

import requests

log = logging.getLogger(__name__)

try:
    import trafilatura
    _HAVE_TRAFILATURA = True
except Exception:  # pragma: no cover - optional at import time
    _HAVE_TRAFILATURA = False

from bs4 import BeautifulSoup

# Tags that are almost never part of the substantive "values" body text.
_STRIP_TAGS = ("script", "style", "nav", "footer", "header", "aside",
               "form", "noscript", "svg", "button")


def fetch_html(url: str, session: requests.Session, *, timeout: int = 45) -> str | None:
    """Fetch a Wayback raw-capture URL, following redirect chains.

    Returns decoded HTML text, or None on failure. `allow_redirects=True` lets
    us transparently follow a captured 301/302 chain to the page that actually
    held content that year.
    """
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Fetch failed %s: %s", url, exc)
        return None
    # Wayback occasionally serves a "snapshot not found" 200 page; callers can
    # additionally guard on extracted text length.
    return resp.text


def extract_clean_text(html: str, source_url: str = "") -> str:
    """Extract visible body text, stripping navigation/footer/boilerplate."""
    if not html:
        return ""

    if _HAVE_TRAFILATURA:
        text = trafilatura.extract(
            html,
            url=source_url or None,
            include_comments=False,
            include_tables=False,
            favor_recall=True,          # keep more body text from sparse pages
            no_fallback=False,
        )
        if text and len(text.strip()) >= 40:
            return _collapse_ws(text)

    # Fallback: strip obvious chrome, take remaining visible text.
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return _collapse_ws(text)


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_compare(text: str) -> str:
    """Lowercase + collapse whitespace, for hashing and similarity.

    Strips case and spacing noise so that a pure reformat doesn't read as a
    content change, while genuine copy edits still do.
    """
    return _collapse_ws(text.lower())


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def text_changed(
    prev_clean: str | None,
    curr_clean: str,
    *,
    similarity_threshold: float = 0.95,
) -> tuple[bool | None, float | None]:
    """Did the page change vs. the prior year?

    Returns (changed, similarity_ratio):
      * (None, None)  if there is no prior year to compare against.
      * (False, 1.0)  if normalized text is byte-identical.
      * (changed, r)  otherwise, where r is a 0..1 SequenceMatcher ratio and
                      `changed` is True when r < similarity_threshold.

    The 0.95 threshold tolerates trivial drift (a changed copyright year, a
    reworded CTA) while flagging real revisions. It is a tunable parameter, not
    a fact; surfaced in the README as a documented choice.
    """
    if prev_clean is None:
        return None, None
    a, b = normalize_for_compare(prev_clean), normalize_for_compare(curr_clean)
    if a == b:
        return False, 1.0
    ratio = SequenceMatcher(None, a, b).ratio()
    return (ratio < similarity_threshold), round(ratio, 4)
