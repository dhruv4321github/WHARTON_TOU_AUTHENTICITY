"""
SEC EDGAR source for Part 2: definitive proxy statements (DEF 14A).

Why proxies via EDGAR (documented choice)
-----------------------------------------
The brief allows ONE of {ESG report, sustainability report, DEI report, proxy
statement}. The first three are *voluntary* PDFs hosted on company IR pages or
third-party aggregators -> patchy coverage and no clean, scalable API. DEF 14A
proxy statements are *mandatory annual* SEC filings, so EDGAR carries them for
essentially every firm, every year, behind an official, documented,
rate-limit-friendly API. That yields near-complete 2016-2024 coverage for all 50
firms and scales cleanly to the full S&P 500. Proxies are also substantively apt
for "lived values": they disclose governance, executive pay, board
composition/diversity, and (increasingly) human-capital and ESG oversight — which
map onto the shared 10-category taxonomy used in Parts 1-3.

EDGAR etiquette (https://www.sec.gov/os/accessing-edgar-data): a descriptive
User-Agent with contact info, and <=10 requests/sec. Everything is cached by
(ticker, year) so re-runs and the mining pass never re-hit EDGAR.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from config.companies import Company

log = logging.getLogger("part2.edgar")


@dataclass
class ReportRef:
    """One resolved filing (or a recorded gap) for a company-year."""
    ticker: str
    year: int
    url: str
    source: str            # "edgar"
    local_path: str = ""
    status: str = ""       # "downloaded" | "cached" | "download_failed" | "not_found"

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUB_URL = "https://data.sec.gov/submissions/{name}"
FORM = "DEF 14A"

# Ticker->CIK overrides for firms whose CURRENT CIK (from company_tickers.json)
# lacks filing history because of a reorganization. BlackRock did a 2024 holding-
# company reorg: the ticker now resolves to a NEW CIK with only 2025+ filings, so
# we pin the predecessor CIK to recover the 2016-2024 proxies. Verified each
# predecessor carries the full 9-year DEF 14A history.
CIK_OVERRIDES: dict[str, str] = {
    "BLK": "0001364742",   # legacy "BlackRock, Inc." (pre-2024 holding-co reorg)
}

_cik_cache: dict[str, str] = {}


def _load_ticker_map(session: requests.Session) -> dict[str, str]:
    """{TICKER -> zero-padded 10-digit CIK} from EDGAR's official mapping (cached)."""
    global _cik_cache
    if _cik_cache:
        return _cik_cache
    r = session.get(_TICKERS_URL, timeout=30)
    r.raise_for_status()
    _cik_cache = {row["ticker"].upper(): str(row["cik_str"]).zfill(10)
                  for row in r.json().values()}
    return _cik_cache


def ticker_to_cik(ticker: str, session: requests.Session) -> str | None:
    """Map our ticker to a CIK, tolerating dot/dash class shares (BRK.B -> BRK-B)."""
    if ticker.upper() in CIK_OVERRIDES:    # reorg predecessors (see CIK_OVERRIDES)
        return CIK_OVERRIDES[ticker.upper()]
    m = _load_ticker_map(session)
    for cand in (ticker.upper(), ticker.upper().replace(".", "-"), ticker.upper().replace(".", "")):
        if cand in m:
            return m[cand]
    return None


def _all_def14a(cik: str, session: requests.Session, *, sleep: float = 0.2
                ) -> list[tuple[str, str, str]]:
    """All DEF 14A filings as [(filingDate, accessionNumber, primaryDocument)].

    The submissions API keeps only the most recent ~1000 filings inline under
    `filings.recent`; older ones live in shard files listed under `filings.files`.
    Large firms file constantly, so we MUST read the shards to reach 2016 proxies.
    """
    out: list[tuple[str, str, str]] = []

    def harvest(block: dict) -> None:
        for f, d, a, doc in zip(block.get("form", []), block.get("filingDate", []),
                                block.get("accessionNumber", []), block.get("primaryDocument", [])):
            if f == FORM:
                out.append((d, a, doc))

    r = session.get(_SUB_URL.format(name=f"CIK{cik}.json"), timeout=30)
    r.raise_for_status()
    data = r.json()
    harvest(data.get("filings", {}).get("recent", {}))
    for shard in data.get("filings", {}).get("files", []):
        time.sleep(sleep)
        rr = session.get(_SUB_URL.format(name=shard["name"]), timeout=30)
        if rr.ok:
            harvest(rr.json())
    return out


def resolve_company(company: Company, session: requests.Session,
                    from_year: int, to_year: int, *, sleep: float = 0.2) -> list[ReportRef]:
    """One DEF 14A per year (newest filing in each calendar year) as ReportRefs."""
    cik = ticker_to_cik(company.ticker, session)
    if not cik:
        log.warning("[%s] no CIK on EDGAR", company.ticker)
        return [ReportRef(company.ticker, y, "", "edgar", status="not_found")
                for y in range(from_year, to_year + 1)]

    by_year: dict[int, str] = {}
    for d, a, doc in sorted(_all_def14a(cik, session, sleep=sleep)):  # ascending date
        y = int(d[:4])
        if from_year <= y <= to_year and doc:
            acc = a.replace("-", "")
            # newest filing in the year wins (later dates overwrite earlier)
            by_year[y] = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"

    refs = []
    for y in range(from_year, to_year + 1):
        if y in by_year:
            refs.append(ReportRef(company.ticker, y, by_year[y], "edgar"))
        else:
            refs.append(ReportRef(company.ticker, y, "", "edgar", status="not_found"))
    return refs


def download(ref: ReportRef, session: requests.Session, cache_dir: Path,
             *, timeout: int = 90) -> ReportRef:
    """Download a filing's primary document (HTML), caching by (ticker, year)."""
    if not ref.url:
        return ref
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{ref.ticker}_{ref.year}.htm"
    if path.exists() and path.stat().st_size > 2048:
        ref.local_path, ref.status = str(path), "cached"
        return ref
    try:
        resp = session.get(ref.url, timeout=timeout)
        resp.raise_for_status()
        if len(resp.content) < 2048:          # truncated / error stub, not a real filing
            ref.status = "download_failed"
            return ref
        path.write_bytes(resp.content)
        ref.local_path, ref.status = str(path), "downloaded"
    except requests.RequestException as exc:
        log.warning("[%s %d] download failed: %s", ref.ticker, ref.year, exc)
        ref.status = "download_failed"
    return ref
