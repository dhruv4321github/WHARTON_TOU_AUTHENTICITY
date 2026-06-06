"""
Part 1 orchestrator: build the stated-values snapshot dataset.

    python -m part1_stated_values.collect --out-dir data/part1

For each company it:
  1. Probes candidate URLs against CDX and keeps the best-covered one.
  2. Selects one capture per year (2016-2024).
  3. Fetches + cleans each snapshot (with an on-disk HTML cache so re-runs are
     free and the Wayback Machine isn't re-hit).
  4. Computes deterministic change-from-prior.
  5. Writes one row per company-year plus a coverage report.

The theme_categories and analyst_notes columns are emitted EMPTY here; they are
filled by the separate LLM analysis step (part1_stated_values/analyze.py), so
that the expensive interpretive pass runs on already-clean, cached text.

Scaling note: nothing here assumes 50 companies. Swap in the full S&P 500 seed
list and the same code runs; the cache + polite rate limiting are what make
~4,500 snapshots feasible rather than ~450.
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.companies import COMPANIES, Company, candidate_urls
from part1_stated_values import cdx, extract

log = logging.getLogger("part1.collect")

COLUMNS = [
    "ticker", "company_name", "sector", "year",
    "snapshot_timestamp", "snapshot_url", "source_url", "http_status",
    "page_text_clean", "text_char_len", "text_sha1",
    "similarity_to_prior", "changed_from_prior",
    "coverage_status", "theme_categories", "analyst_notes",
]


def build_session(user_agent: str) -> requests.Session:
    """A retrying, polite session. Wayback rate-limits aggressively; back off."""
    session = requests.Session()
    session.headers["User-Agent"] = user_agent
    retry = Retry(
        total=4, backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def choose_best_url(company: Company, session: requests.Session,
                    from_year: int, to_year: int,
                    cdx_timeout: int = 60) -> tuple[str, list[cdx.Capture]]:
    """Probe every candidate URL; return the best one to represent this company.

    Selection key (largest tuple wins):
      1. COVERAGE — how many of the target years the candidate is archived for.
         Longitudinal completeness is the primary goal, so this dominates: a
         strictly better-covered page always wins, even the bare domain.
      2. AUTHOR RANK — on a coverage TIE, prefer the candidate listed EARLIER in
         the company's ordered candidate list (config/companies.py). This is the
         "path preference" fix: a dedicated values path (jpmorganchase.com/about)
         is listed before the bare domain, so we pick it instead of the busier-
         but-generic homepage that the old capture-count tiebreak chose. It is
         expressed via author ordering rather than a raw "URL has a slash" test so
         that firms whose values page genuinely IS a bare subdomain root — Amazon
         (aboutamazon.com), Meta (about.meta.com) — which list "" first, are
         preserved. The human judgment lives once, in companies.py.
      3. CAPTURE COUNT — final tiebreak (a busier page is usually the canonical one).

    Returns ("", []) if nothing is archived for any candidate -> recorded as a
    fully-missing company, not a crash.
    """
    best_url, best_caps, best_key = "", [], (-1, 0, -1)
    for rank, url in enumerate(candidate_urls(company)):
        caps = cdx.query_cdx(url, session, from_year, to_year, timeout=cdx_timeout)
        if not caps:
            continue
        # -rank: an EARLIER candidate (smaller rank) ranks HIGHER on a coverage tie.
        key = (cdx.coverage_score(caps, from_year, to_year), -rank, len(caps))
        if key > best_key:
            best_url, best_caps, best_key = url, caps, key
        time.sleep(0.3)  # be polite between probes
    return best_url, best_caps


def collect_company(company: Company, session: requests.Session, *,
                    from_year: int, to_year: int, cache_dir: Path,
                    sleep: float, cdx_timeout: int = 60) -> list[dict]:
    log.info("[%s] %s", company.ticker, company.name)
    best_url, caps = choose_best_url(company, session, from_year, to_year, cdx_timeout)

    if not best_url:
        # No archived page found for any candidate; emit empty rows so the gap
        # is explicit and auditable in the final dataset.
        return [_empty_row(company, year, "no_page_found") for year in range(from_year, to_year + 1)]

    log.info("    chosen URL: %s  (%d captures)", best_url, len(caps))
    chosen = cdx.select_one_per_year(caps, from_year, to_year)

    rows, prev_clean = [], None
    for year in range(from_year, to_year + 1):
        cap = chosen[year]
        if cap is None:
            rows.append(_empty_row(company, year, "no_snapshot_in_year",
                                   source_url=best_url))
            # We do NOT carry prev_clean across a gap; change detection resumes
            # only between two consecutive *present* years (documented).
            prev_clean = None
            continue

        html = _cached_fetch(cap, session, cache_dir)
        clean = extract.extract_clean_text(html or "", cap.original)
        changed, sim = extract.text_changed(prev_clean, clean)
        status = "ok" if len(clean) >= 80 else "thin_text"

        rows.append({
            "ticker": company.ticker,
            "company_name": company.name,
            "sector": company.sector,
            "year": year,
            "snapshot_timestamp": cap.timestamp,
            "snapshot_url": cap.raw_url(),
            "source_url": best_url,
            "http_status": cap.statuscode,
            "page_text_clean": clean,
            "text_char_len": len(clean),
            "text_sha1": extract.sha1(extract.normalize_for_compare(clean)) if clean else "",
            "similarity_to_prior": sim,
            "changed_from_prior": changed,
            "coverage_status": status,
            "theme_categories": "",   # filled by analyze.py (LLM step)
            "analyst_notes": "",      # filled by analyze.py (LLM step)
        })
        prev_clean = clean if clean else prev_clean
        time.sleep(sleep)
    return rows


def _cached_fetch(cap: cdx.Capture, session: requests.Session, cache_dir: Path) -> str | None:
    """Fetch raw HTML, caching by capture timestamp+digest so re-runs are free."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = f"{cap.timestamp}_{cap.digest}.html"
    path = cache_dir / key
    if path.exists():
        return path.read_text(encoding="utf-8", errors="ignore")
    html = extract.fetch_html(cap.raw_url(), session)
    if html is not None:
        path.write_text(html, encoding="utf-8", errors="ignore")
    return html


def _empty_row(company: Company, year: int, status: str, source_url: str = "") -> dict:
    return {
        "ticker": company.ticker, "company_name": company.name,
        "sector": company.sector, "year": year,
        "snapshot_timestamp": "", "snapshot_url": "", "source_url": source_url,
        "http_status": "", "page_text_clean": "", "text_char_len": 0,
        "text_sha1": "", "similarity_to_prior": None, "changed_from_prior": None,
        "coverage_status": status, "theme_categories": "", "analyst_notes": "",
    }


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-company coverage summary: years with usable text, and listed gaps."""
    def summarize(g: pd.DataFrame) -> pd.Series:
        usable = g[g["coverage_status"] == "ok"]
        gap_years = sorted(g.loc[g["coverage_status"] != "ok", "year"].tolist())
        return pd.Series({
            "sector": g["sector"].iloc[0],
            "years_total": g["year"].nunique(),
            "years_usable": usable["year"].nunique(),
            "source_url": g["source_url"].replace("", pd.NA).dropna().iloc[0]
                          if g["source_url"].any() else "",
            "gap_years": ";".join(map(str, gap_years)),
        })
    return (df.groupby("ticker", sort=False)
              .apply(summarize, include_groups=False)
              .reset_index())


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect Part 1 stated-values snapshots.")
    ap.add_argument("--out-dir", default="data/part1", type=Path)
    ap.add_argument("--cache-dir", default="data/part1/_html_cache", type=Path)
    ap.add_argument("--from-year", default=2016, type=int)
    ap.add_argument("--to-year", default=2024, type=int)
    ap.add_argument("--sleep", default=0.5, type=float, help="seconds between fetches")
    ap.add_argument("--cdx-timeout", default=60, type=int,
                    help="per-CDX-query timeout (s); raise when web.archive.org is slow")
    ap.add_argument("--only", nargs="*", help="restrict to these tickers (debug)")
    ap.add_argument("--limit", type=int, help="first N companies only (debug)")
    ap.add_argument("--user-agent",
                    default="Wharton-TAU-Lab research RA task (academic; contact: you@example.com)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session = build_session(args.user_agent)

    companies = list(COMPANIES)
    if args.only:
        wanted = {t.upper() for t in args.only}
        companies = [c for c in companies if c.ticker.upper() in wanted]
    if args.limit:
        companies = companies[: args.limit]

    all_rows: list[dict] = []
    for c in companies:
        all_rows.extend(collect_company(
            c, session,
            from_year=args.from_year, to_year=args.to_year,
            cache_dir=args.cache_dir, sleep=args.sleep,
            cdx_timeout=args.cdx_timeout,
        ))

    df = pd.DataFrame(all_rows, columns=COLUMNS)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_dir / "part1_stated_values.csv", index=False)
    df.to_parquet(args.out_dir / "part1_stated_values.parquet", index=False)
    coverage_report(df).to_csv(args.out_dir / "part1_coverage_report.csv", index=False)

    usable = (df["coverage_status"] == "ok").sum()
    log.info("\nDone. %d rows, %d with usable text (%.0f%% of %d target snapshots).",
             len(df), usable, 100 * usable / max(len(df), 1), len(df))
    log.info("Wrote dataset + coverage report to %s", args.out_dir)


if __name__ == "__main__":
    main()
