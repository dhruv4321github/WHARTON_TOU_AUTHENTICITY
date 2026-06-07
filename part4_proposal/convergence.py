"""
Part 4 (exploratory) — Is rising say–do alignment genuine, or institutional herding?

Part 3 produced a headline finding: peer-relative say↔do alignment ROSE across the
sample from ~-0.02 (2016) to +0.20 (2024). The natural reading is optimistic — firms
are increasingly "walking their talk." This module interrogates that reading instead
of celebrating it.

THE ALTERNATIVE HYPOTHESIS (institutional isomorphism; DiMaggio & Powell 1983).
Over 2016–2024 the whole corporate field adopted a common stakeholder / ESG /
human-capital vocabulary — sustainability, diversity, purpose, community. If EVERY
firm drifts onto the same script in BOTH what it says (websites) and what it discloses
(proxies), then:
  * firms look more alike each year (cross-firm dispersion FALLS), and
  * the two genres mechanically point the same way, inflating RAW say–do alignment,
without any individual firm genuinely closing its own authenticity gap. That would be
*mimetic convergence*, not authenticity — a legitimacy bandwagon.

WHAT WE MEASURE.
For each year we compute the cross-firm DISPERSION of the stated profiles and of the
disclosed profiles — the average distance of firms from that year's centroid:

  * mean_l2_to_centroid  — average Euclidean distance of firms to the year centroid.
      This is exactly the average MAGNITUDE of the deviation vectors that Part 3's
      *centered* cosine runs on (Part 3 centers each side on its year mean). So this
      one number does double duty: it is our convergence metric AND a direct bridge
      to Part 3 — if it shrinks, Part 3's peer-relative signal is being computed on
      ever-fainter deviations.
  * mean_cosdist_to_centroid — average cosine distance to the centroid (shape-only
      spread; complements L2, which also reflects magnitude).

If dispersion declines over time → the field is converging (herding evidence).

WHY THIS DISENTANGLES "MECHANICAL" FROM "GENUINE".
  * RAW alignment (genre-confounded) rises mechanically under convergence: both
    genres slide toward one shared centroid, so cosine(say, do) climbs for everyone.
  * CENTERED alignment (Part 3's primary measure) removes the year mean, so pure
    convergence does NOT inflate it — it SHRINKS the deviation vectors and makes the
    cosine noisier. So if centered alignment rose *while* dispersion fell, the rise
    is NOT explained away by herding (it survived a shrinking signal) — but the late-
    window centered numbers rest on fainter deviations, a caveat for Part 3.
We therefore print RAW and CENTERED alignment by year next to the dispersion trend.

PER-CATEGORY: which themes converged? We also track each category's cross-firm SD by
year and compare an early window (≤2018) to a late one (≥2022). The isomorphism story
predicts the *ESG-bandwagon* themes (sustainability, diversity, people, community)
converged most.

Inputs : data/part1/part1_stated_values_analyzed.csv   (via Part 3 loader → say_<cat>)
         data/part2/part2_lived_values.csv             (via Part 3 loader → do_<cat>)
         data/part3/authenticity_index.csv             (raw/centered alignment by year)
Outputs: data/part4/convergence_by_year.csv
         data/part4/convergence_by_category.csv
         data/part4/fig_*.png   (with --plots)

    PYTHONPATH=. python -m part4_proposal.convergence --plots
"""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse Part 3's harmonization so "say" and "do" profiles are defined identically
# here and in the index (same L1-normalized 10-vectors, same dropped-empty rule).
from part3_authenticity_index.build_index import load_stated, load_disclosed, CATS

log = logging.getLogger("part4.convergence")

SAY = [f"say_{c}" for c in CATS]
DO = [f"do_{c}" for c in CATS]
EARLY_MAX = 2018   # "early window" = first three years (2016–2018)
LATE_MIN = 2022    # "late window"  = last three years  (2022–2024)


# --------------------------------------------------------------------------- #
# Cross-firm dispersion per year
# --------------------------------------------------------------------------- #
def centroid_dispersion(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Per year: how spread out are firms around that year's mean profile?

    mean_l2_to_centroid    — mean Euclidean distance to the year centroid; this is the
                             average magnitude of the deviation vectors Part 3 centers
                             on, so a falling value both signals convergence AND tells
                             us Part 3's peer-relative signal is fading.
    mean_cosdist_to_centroid — mean cosine distance to the centroid (shape-only spread).
    """
    rows = []
    for y, g in df.groupby("year"):
        M = g[cols].to_numpy(float)          # (n_firms, 10) distributions
        n = M.shape[0]
        if n < 2:
            continue                         # dispersion is undefined for <2 firms
        centroid = M.mean(axis=0)
        l2 = np.linalg.norm(M - centroid, axis=1)
        cn = np.linalg.norm(centroid)
        rn = np.linalg.norm(M, axis=1)
        cosdist = 1.0 - (M @ centroid) / (rn * cn)   # norms > 0 (rows are distributions)
        rows.append(dict(year=int(y), n_firms=n,
                         mean_l2_to_centroid=round(float(l2.mean()), 5),
                         mean_cosdist_to_centroid=round(float(cosdist.mean()), 5)))
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def ols_trend(years, values) -> tuple[float, float, int]:
    """Hand-rolled OLS slope of `values` on `year`, with a t-stat for the slope.
    No scipy — same convention as Part 2's paired tests. Returns (slope, t, dof)."""
    x = np.asarray(years, float)
    y = np.asarray(values, float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), max(n - 2, 0)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    slope = ((x - xm) * (y - ym)).sum() / sxx
    intercept = ym - slope * xm
    resid = y - (intercept + slope * x)
    dof = n - 2
    se = math.sqrt((resid ** 2).sum() / dof / sxx)
    t = slope / se if se > 0 else float("nan")
    return slope, t, dof


# --------------------------------------------------------------------------- #
# Per-category convergence (which themes herded?)
# --------------------------------------------------------------------------- #
def category_dispersion(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Per year, cross-firm standard deviation of each category's share."""
    rows = []
    for y, g in df.groupby("year"):
        if len(g) < 2:
            continue
        rec = {"year": int(y), "n_firms": len(g)}
        for col, cat in zip(cols, CATS):
            rec[cat] = float(g[col].std(ddof=1))
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def early_late_delta(cat_disp: pd.DataFrame, side: str) -> pd.DataFrame:
    """Per category: mean cross-firm SD early (≤2018) vs late (≥2022) + % change.
    Negative pct_change = the field's firms converged on that theme over the window."""
    early = cat_disp[cat_disp.year <= EARLY_MAX][CATS].mean()
    late = cat_disp[cat_disp.year >= LATE_MIN][CATS].mean()
    out = pd.DataFrame({
        "side": side,
        "category": CATS,
        "sd_early_2016_2018": early.round(5).to_numpy(),
        "sd_late_2022_2024": late.round(5).to_numpy(),
    })
    out["delta"] = (out.sd_late_2022_2024 - out.sd_early_2016_2018).round(5)
    out["pct_change"] = ((out.delta / out.sd_early_2016_2018) * 100).round(1)
    return out.sort_values("pct_change").reset_index(drop=True)   # most-converged first


# --------------------------------------------------------------------------- #
# Bridge to Part 3: raw vs centered alignment by year
# --------------------------------------------------------------------------- #
def alignment_by_year(index_path: Path) -> pd.DataFrame:
    idx = pd.read_csv(index_path)
    g = idx.groupby("year").agg(
        n=("ticker", "size"),
        raw_alignment=("align_cosine_raw", "mean"),
        centered_alignment=("align_cosine_centered", "mean"),
    ).reset_index()
    g[["raw_alignment", "centered_alignment"]] = g[["raw_alignment", "centered_alignment"]].round(4)
    return g


# --------------------------------------------------------------------------- #
# Plots (lazy import; graceful if matplotlib missing)
# --------------------------------------------------------------------------- #
def make_plots(say_disp, do_disp, cat_delta_do, align, out_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log.warning("matplotlib not installed — skipping plots.")
        return

    # 1) Dispersion over time: do firms converge? (y-axis from 0 = honest scale)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(do_disp.year, do_disp.mean_l2_to_centroid, "o-", label="Disclosed (proxies, dense)", color="#1f77b4")
    ax.plot(say_disp.year, say_disp.mean_l2_to_centroid, "s--", label="Stated (websites, sparse)", color="#ff7f0e")
    ax.set_ylim(bottom=0)   # don't visually exaggerate a mild trend
    ax.set_xlabel("Year"); ax.set_ylabel("Cross-firm dispersion\n(mean L2 distance to year centroid)")
    ax.set_title("Are firms converging on a common values vocabulary?")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_dir / "fig_dispersion_over_time.png", dpi=130); plt.close(fig)

    # 2) Which themes converged? (% change in cross-firm SD, disclosed side = robust)
    fig, ax = plt.subplots(figsize=(8, 5))
    d = cat_delta_do.sort_values("pct_change")
    # NB: use bracket access — `pct_change` is also a DataFrame METHOD, so `d.pct_change`
    # returns the bound method, not the column.
    colors = ["#2ca02c" if v < 0 else "#d62728" for v in d["pct_change"]]
    ax.barh(d["category"], d["pct_change"], color=colors)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("% change in cross-firm SD, early (≤2018) → late (≥2022)")
    ax.set_title("Theme convergence in disclosures\n(green = firms became more alike on this theme)")
    fig.tight_layout(); fig.savefig(out_dir / "fig_theme_convergence.png", dpi=130); plt.close(fig)

    # 3) The money chart: dispersion falling vs Part 3 alignment rising (twin axis)
    fig, ax1 = plt.subplots(figsize=(8.5, 5))
    ax1.plot(do_disp.year, do_disp.mean_l2_to_centroid, "o-", color="#1f77b4",
             label="Disclosed dispersion (L2)")
    ax1.set_xlabel("Year"); ax1.set_ylabel("Cross-firm dispersion (disclosed)", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4"); ax1.set_ylim(bottom=0)
    ax2 = ax1.twinx()
    ax2.plot(align.year, align.raw_alignment, "^--", color="#9467bd", label="Part 3 RAW alignment")
    ax2.plot(align.year, align.centered_alignment, "v--", color="#d62728", label="Part 3 CENTERED alignment")
    ax2.set_ylabel("Part 3 say–do alignment (cosine)")
    ax2.axhline(0, color="grey", lw=0.6, ls=":")
    # only the labelled data series in the legend (skip the axhline reference line)
    lines = [l for l in ax1.get_lines() + ax2.get_lines() if not l.get_label().startswith("_")]
    ax1.legend(lines, [l.get_label() for l in lines], loc="center left", fontsize=8)
    ax1.set_title("Convergence vs. alignment: is the Part 3 rise mechanical?")
    fig.tight_layout(); fig.savefig(out_dir / "fig_convergence_vs_alignment.png", dpi=130); plt.close(fig)
    log.info("Wrote 3 figures to %s", out_dir)


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Part 4: mimetic-convergence interrogation of the authenticity index.")
    ap.add_argument("--part1", default="data/part1/part1_stated_values_analyzed.csv", type=Path)
    ap.add_argument("--part2", default="data/part2/part2_lived_values.csv", type=Path)
    ap.add_argument("--index", default="data/part3/authenticity_index.csv", type=Path)
    ap.add_argument("--out-dir", default="data/part4", type=Path)
    ap.add_argument("--plots", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    stated = load_stated(args.part1)        # genuine themed company-years (no carry-forward)
    disclosed = load_disclosed(args.part2)

    say_disp = centroid_dispersion(stated, SAY)
    do_disp = centroid_dispersion(disclosed, DO)
    align = alignment_by_year(args.index)

    # merge the by-year views into one tidy table
    by_year = (do_disp.rename(columns={c: f"do_{c}" for c in
                                       ["n_firms", "mean_l2_to_centroid", "mean_cosdist_to_centroid"]})
               .merge(say_disp.rename(columns={c: f"say_{c}" for c in
                                               ["n_firms", "mean_l2_to_centroid", "mean_cosdist_to_centroid"]}),
                      on="year", how="outer")
               .merge(align, on="year", how="left")
               .sort_values("year"))
    by_year.to_csv(args.out_dir / "convergence_by_year.csv", index=False)

    cat_do = category_dispersion(disclosed, DO)
    cat_say = category_dispersion(stated, SAY)
    cat_delta_do = early_late_delta(cat_do, "disclosed")
    cat_delta_say = early_late_delta(cat_say, "stated")
    cat_out = pd.concat([cat_delta_do, cat_delta_say], ignore_index=True)
    cat_out.to_csv(args.out_dir / "convergence_by_category.csv", index=False)

    # ---- console summary (the actual findings) ----
    s_slope, s_t, _ = ols_trend(say_disp.year, say_disp.mean_l2_to_centroid)
    d_slope, d_t, _ = ols_trend(do_disp.year, do_disp.mean_l2_to_centroid)
    log.info("\n=== CROSS-FIRM DISPERSION OVER TIME (mean L2 distance to year centroid) ===")
    log.info("Disclosed (proxies): %.4f (2016) → %.4f (2024); OLS slope=%.5f/yr, t=%.2f",
             do_disp.mean_l2_to_centroid.iloc[0], do_disp.mean_l2_to_centroid.iloc[-1], d_slope, d_t)
    log.info("Stated  (websites):  %.4f (%d) → %.4f (%d); OLS slope=%.5f/yr, t=%.2f",
             say_disp.mean_l2_to_centroid.iloc[0], say_disp.year.iloc[0],
             say_disp.mean_l2_to_centroid.iloc[-1], say_disp.year.iloc[-1], s_slope, s_t)
    log.info("  (negative slope ⇒ firms converging on a common profile = herding evidence)")

    log.info("\n=== BRIDGE TO PART 3 — alignment by year vs dispersion ===")
    log.info(align.to_string(index=False))

    log.info("\n=== WHICH THEMES CONVERGED MOST (disclosed; early≤2018 → late≥2022 SD) ===")
    log.info(cat_delta_do[["category", "sd_early_2016_2018", "sd_late_2022_2024", "pct_change"]]
             .head(5).to_string(index=False))

    log.info("\nWrote convergence_by_year.csv and convergence_by_category.csv to %s", args.out_dir)
    if args.plots:
        make_plots(say_disp, do_disp, cat_delta_do, align, args.out_dir)


if __name__ == "__main__":
    main()
