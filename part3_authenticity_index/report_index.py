"""
Part 3 — report on the authenticity index: distributional properties, validity
checks, and plots, all from the committed index (no recomputation of the measure).

Covers the brief's three reporting asks for Part 3:
  * basic DISTRIBUTIONAL properties (overall, by sector, over time);
  * at least one VALIDITY CHECK — we run three:
      (V1) face validity  — do the firms at the top/bottom make intuitive sense?
      (V2) stability      — is the index a STABLE firm trait (between-firm variance
                            >> within-firm variance), i.e. signal not yearly noise?
      (V3) centering pays  — raw vs. peer-relative ranking differ, confirming the
                            centered measure removes the document-genre baseline.

    PYTHONPATH=. python -m part3_authenticity_index.report_index [--plots]
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger("part3.report")

PRIMARY = "align_cosine_centered"   # the headline measure


# --------------------------------------------------------------------------- #
def distributions(idx: pd.DataFrame, out_dir: Path) -> None:
    """Overall + by-sector + by-year distributional properties."""
    log.info("=== DISTRIBUTION: company-year %s (primary measure) ===", PRIMARY)
    log.info(idx[PRIMARY].describe().round(3).to_string())
    log.info("  raw cosine mean (genre-confounded, for contrast): %.3f",
             idx["align_cosine_raw"].mean())
    log.info("  share of company-years with NEGATIVE alignment (say-do inversion): %.0f%%",
             100 * (idx[PRIMARY] < 0).mean())

    by_sector = (idx.groupby("sector")[PRIMARY]
                   .agg(["count", "mean", "std", "min", "max"]).round(3)
                   .sort_values("mean", ascending=False))
    log.info("\n=== by SECTOR ===\n%s", by_sector.to_string())

    by_year = idx.groupby("year")[PRIMARY].agg(["count", "mean"]).round(3)
    log.info("\n=== by YEAR (does it move over time?) ===\n%s", by_year.to_string())

    by_sector.to_csv(out_dir / "authenticity_by_sector.csv")
    by_year.to_csv(out_dir / "authenticity_by_year.csv")


# --------------------------------------------------------------------------- #
def validity(idx: pd.DataFrame, firms: pd.DataFrame) -> None:
    # ---- V1: face validity -------------------------------------------------
    log.info("\n=== VALIDITY 1 — face validity (top / bottom firms) ===")
    cols = ["ticker", "company_name", "sector", "n_years_scored", "mean_cosine_centered"]
    log.info("Most authentic (stated≈disclosed positioning):\n%s",
             firms.head(5)[cols].to_string(index=False))
    log.info("Least authentic (stated diverges from disclosed):\n%s",
             firms.tail(5)[cols].to_string(index=False))
    # what theme drives the lowest firm's gap (illustrative)
    low = firms.iloc[-1].ticker
    g = idx[idx.ticker == low]
    log.info("  e.g. %s: says '%s', discloses '%s'; most under-disclosed vs talk = '%s'.",
             low, g.top_say.mode().iloc[0], g.top_do.mode().iloc[0],
             g.largest_underclaim.mode().iloc[0])

    # ---- V2: stability (between-firm vs within-firm) -----------------------
    firm_means = idx.groupby("ticker")[PRIMARY].mean()
    between_sd = firm_means.std(ddof=1)
    within_sd = idx.groupby("ticker")[PRIMARY].std(ddof=1).mean()  # avg within-firm sd
    multi = idx.groupby("ticker").size()
    icc_like = between_sd**2 / (between_sd**2 + within_sd**2)
    log.info("\n=== VALIDITY 2 — stability (is it a firm trait or yearly noise?) ===")
    log.info("  between-firm sd = %.3f vs within-firm sd = %.3f  →  variance-share between firms ≈ %.0f%%",
             between_sd, within_sd, 100 * icc_like)
    log.info("  (between >> within ⇒ the index captures stable firm differences, "
             "not year-to-year noise; %d of %d firms have >1 scored year)",
             (multi > 1).sum(), len(multi))

    # ---- V3: centering changes the ranking ---------------------------------
    r = firms[["mean_cosine_raw", "mean_cosine_centered"]].corr().iloc[0, 1]
    raw_rank = firms.set_index("ticker")["mean_cosine_raw"].rank(ascending=False)
    cen_rank = firms.set_index("ticker")["mean_cosine_centered"].rank(ascending=False)
    spearman = raw_rank.corr(cen_rank)
    log.info("\n=== VALIDITY 3 — peer-relative centering is doing work ===")
    log.info("  corr(raw, centered) firm means = %.2f ; Spearman rank corr = %.2f", r, spearman)
    log.info("  (well below 1.0 ⇒ removing the genre/year baseline meaningfully "
             "re-orders firms — raw alignment was partly measuring document type)")


# --------------------------------------------------------------------------- #
def make_plots(idx: pd.DataFrame, firms: pd.DataFrame, out_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log.warning("matplotlib not installed — skipping --plots.")
        return

    # (a) histogram of company-year centered alignment
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(idx[PRIMARY].dropna(), bins=25, color="C0", edgecolor="white")
    ax.axvline(0, color="k", lw=1, ls="--")
    ax.set(title="Authenticity index — company-year distribution (peer-relative cosine)",
           xlabel="stated↔disclosed alignment (−1 inversion … +1 aligned)",
           ylabel="company-years")
    fig.tight_layout(); fig.savefig(out_dir / "fig_authenticity_hist.png", dpi=130); plt.close(fig)

    # (b) by sector (mean ± sd)
    bs = idx.groupby("sector")[PRIMARY].agg(["mean", "std"]).sort_values("mean")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(bs.index, bs["mean"], xerr=bs["std"], color="C2", capsize=4)
    ax.axvline(0, color="k", lw=1)
    ax.set(title="Authenticity by sector (mean ± sd)", xlabel="peer-relative alignment")
    fig.tight_layout(); fig.savefig(out_dir / "fig_authenticity_by_sector.png", dpi=130); plt.close(fig)

    # (c) over time (overall + per sector)
    fig, ax = plt.subplots(figsize=(8, 5))
    for sec, gs in idx.groupby("sector"):
        ts = gs.groupby("year")[PRIMARY].mean()
        ax.plot(ts.index, ts.values, marker="o", alpha=0.6, label=sec)
    overall = idx.groupby("year")[PRIMARY].mean()
    ax.plot(overall.index, overall.values, marker="s", color="k", lw=2.5, label="ALL")
    ax.axhline(0, color="grey", lw=0.8, ls="--")
    ax.set(title="Authenticity over time, by sector", xlabel="Year",
           ylabel="mean peer-relative alignment")
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out_dir / "fig_authenticity_over_time.png", dpi=130); plt.close(fig)
    log.info("\nWrote 3 figures to %s", out_dir)


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Report on the Part 3 authenticity index.")
    ap.add_argument("--in-dir", default="data/part3", type=Path)
    ap.add_argument("--plots", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    idx = pd.read_csv(args.in_dir / "authenticity_index.csv")
    firms = pd.read_csv(args.in_dir / "authenticity_company_level.csv")

    distributions(idx, args.in_dir)
    validity(idx, firms)
    if args.plots:
        make_plots(idx, firms, args.in_dir)


if __name__ == "__main__":
    main()
