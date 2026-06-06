"""
Wayback Machine CDX client and snapshot-selection logic.

Two jobs:
  1. Talk to the CDX API to discover which captures exist for a given URL.
  2. Decide, deterministically, which ONE capture represents each target year.

Everything here is pure-ish and testable: the only side effect is the HTTP
call in `query_cdx`, which is injected via a `requests.Session` so it can be
mocked in tests.

CDX API reference: http://web.archive.org/cdx/search/cdx
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

import requests

log = logging.getLogger(__name__)

CDX_ENDPOINT = "http://web.archive.org/cdx/search/cdx"


@dataclass(frozen=True)
class Capture:
    """One archived snapshot row from the CDX index."""
    timestamp: str          # 14-digit YYYYMMDDhhmmss
    original: str           # the URL as archived
    statuscode: str         # HTTP status at capture time ("200", "301", ...)
    mimetype: str
    digest: str             # content hash; identical digest == byte-identical page

    @property
    def dt(self) -> datetime:
        return datetime.strptime(self.timestamp, "%Y%m%d%H%M%S")

    @property
    def year(self) -> int:
        return int(self.timestamp[:4])

    def raw_url(self) -> str:
        """Wayback URL that returns the ORIGINAL bytes (no toolbar/rewrite).

        The `id_` modifier is important: without it Wayback injects its own
        navigation chrome and rewrites links, which pollutes text extraction.
        """
        return f"https://web.archive.org/web/{self.timestamp}id_/{self.original}"


def query_cdx(
    url_no_scheme: str,
    session: requests.Session,
    from_year: int = 2016,
    to_year: int = 2024,
    *,
    timeout: int = 60,   # CDX can take 40-50s/query when the endpoint is throttled;
                         # a 30s timeout falsely empties real pages (see collect.py).
) -> list[Capture]:
    """Return all 200-OK HTML captures of `url_no_scheme` in the year range.

    We deliberately do NOT collapse by digest here: we want every capture so the
    selector can pick the one nearest our target date, and so we can detect
    year-over-year change accurately. Filtering choices:
      - statuscode:200  -> ignore redirects/errors at the index level (we handle
                           redirect chains separately when fetching).
      - mimetype:text/html -> drop captures of images, feeds, etc. that share the URL.
    """
    params = {
        "url": url_no_scheme,
        "output": "json",
        "from": f"{from_year}0101",
        "to": f"{to_year}1231",
        "filter": ["statuscode:200", "mimetype:text/html"],
        "fl": "timestamp,original,statuscode,mimetype,digest",
        "collapse": "digest",   # adjacent identical captures collapse; cuts noise
        "limit": 5000,
    }
    try:
        resp = session.get(CDX_ENDPOINT, params=params, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("CDX query failed for %s: %s", url_no_scheme, exc)
        return []

    rows = resp.json()
    if not rows or len(rows) < 2:
        return []
    header, *data = rows               # first row is the column header
    idx = {name: i for i, name in enumerate(header)}
    captures = [
        Capture(
            timestamp=r[idx["timestamp"]],
            original=r[idx["original"]],
            statuscode=r[idx["statuscode"]],
            mimetype=r[idx["mimetype"]],
            digest=r[idx["digest"]],
        )
        for r in data
    ]
    return captures


def coverage_score(captures: list[Capture], from_year: int, to_year: int) -> int:
    """How many of the target years this candidate URL has at least one capture for.

    Used to pick the best candidate path per company: more covered years wins.
    """
    years_present = {c.year for c in captures if from_year <= c.year <= to_year}
    return len(years_present)


def select_one_per_year(
    captures: list[Capture],
    from_year: int = 2016,
    to_year: int = 2024,
    *,
    target_month: int = 7,
    target_day: int = 1,
) -> dict[int, Capture | None]:
    """Pick exactly one capture per year, nearest to a fixed mid-year target.

    Why mid-year (July 1)? An "About Us" page edited in, say, March is more
    representative of that calendar year than a Jan-1 or Dec-31 snapshot, which
    can straddle a redesign. Mid-year is an arbitrary-but-defensible anchor; the
    important thing is that it is FIXED and documented, so selection is
    reproducible and unbiased across companies.

    Returns a dict for every year in range; the value is None for years with no
    capture (an explicit, recorded gap rather than a silent omission).
    """
    by_year: dict[int, list[Capture]] = {y: [] for y in range(from_year, to_year + 1)}
    for c in captures:
        if from_year <= c.year <= to_year:
            by_year[c.year].append(c)

    chosen: dict[int, Capture | None] = {}
    for year, caps in by_year.items():
        if not caps:
            chosen[year] = None
            continue
        target = date(year, target_month, target_day)
        chosen[year] = min(caps, key=lambda c: abs((c.dt.date() - target).days))
    return chosen
