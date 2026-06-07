"""
Part 2 analysis — regenerate, reproducibly, the three things the brief asks us to
"apply text mining to analyze", from the committed mined dataset:

  1. Changes in language, tone, and topic emphasis OVER TIME WITHIN COMPANIES
  2. CROSS-COMPANY / CROSS-SECTOR variation
  3. Shifts that COINCIDE WITH EXTERNAL EVENTS we identify as relevant

`mine.py` already bakes the *within-company year-over-year* signal into the row
(`emphasis_shift_cosine`, `word_count_delta_pct`); this module turns the rest of
the analysis — which previously lived only as prose in SUMMARY.md — into committed,
re-runnable tables so every claim in the summary is auditable from one command.

It is deliberately pure pandas/numpy: no network, no API cost, no scipy. Where a
hypothesis test would normally use scipy we compute a paired t-statistic by hand
AND report a nonparametric "fraction of firms that moved up", so a reader can
judge a shift without us overclaiming statistical significance on n≈50 firms.

Inputs : data/part2/part2_lived_values.csv   (the mined dataset)
Outputs: data/part2/analysis_within_company.csv
         data/part2/analysis_sector_fingerprint.csv
         data/part2/analysis_sector_year.csv
         data/part2/analysis_events.csv
         data/part2/fig_*.png                 (only with --plots, needs matplotlib)

    PYTHONPATH=. python -m part2_lived_values.analysis [--plots]
"""

from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from part1_stated_values.analyze import TAXONOMY

log = logging.getLogger("part2.analysis")

# The shared 10-category space (identical order to Part 1 / mine.py) and its
# matching dataset columns. Keeping this derived from TAXONOMY — not hardcoded —
# means the analysis follows automatically if the taxonomy ever changes.
CATS = list(TAXONOMY.keys())
EMPH = [f"emphasis_{c}" for c in CATS]


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_ok(csv_path: Path) -> pd.DataFrame:
    """Load the mined dataset and keep only usable (`coverage_status == ok`) rows.

    Non-ok rows (gaps, duplicates, scanned/empty) carry no emphasis/tone numbers,
    so they are correctly excluded from analysis rather than counted as zeros —
    the same honest-gap policy used throughout the project.
    """
    df = pd.read_csv(csv_path)
    ok = df[df["coverage_status"] == "ok"].copy()
    # Columns that can be empty (first year / after a gap) come back as NaN; coerce
    # defensively so arithmetic never trips on a stray string.
    numeric = EMPH + ["net_tone", "flesch", "emphasis_shift_cosine",
                      "word_count_delta_pct", "lm_uncertainty", "lm_positive",
                      "lm_negative", "llm_concreteness", "llm_forward_orientation"]
    for c in numeric:
        if c in ok.columns:
            ok[c] = pd.to_numeric(ok[c], errors="coerce")
    ok = ok.sort_values(["ticker", "year"]).reset_index(drop=True)
    log.info("Loaded %d usable company-years across %d firms, %d sectors.",
             len(ok), ok["ticker"].nunique(), ok["sector"].nunique())
    return ok


# --------------------------------------------------------------------------- #
# Small stat helpers (no scipy)
# --------------------------------------------------------------------------- #
def cosine_distance(a: np.ndarray, b: np.ndarray) -> float | None:
    """1 - cosine similarity between two emphasis vectors (0 = identical mix)."""
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return None
    return round(1 - float(np.dot(a, b) / (na * nb)), 4)


def paired_shift(pre: pd.Series, post: pd.Series) -> dict:
    """Paired pre/post summary for firms observed in BOTH windows.

    `pre`/`post` are per-firm metric means indexed by ticker. We inner-join on
    ticker (so a firm missing either window is dropped, never imputed), then report:
      * pre_mean / post_mean / abs_delta : levels and average movement
      * pct_change                       : % change in the cross-firm mean
      * frac_increased                   : share of firms that moved up (nonparametric)
      * t_stat                           : paired t = mean(d)/(sd(d)/sqrt(n));
                                           |t| >~ 2 is the usual ~p<.05 rule of thumb,
                                           reported WITHOUT a p-value (no scipy) so we
                                           don't overstate precision on a 50-firm sample.
    """
    j = pd.concat([pre.rename("pre"), post.rename("post")], axis=1).dropna()
    n = len(j)
    if n == 0:
        return dict(n_firms=0, pre_mean=None, post_mean=None, abs_delta=None,
                    pct_change=None, frac_increased=None, t_stat=None)
    d = j["post"] - j["pre"]
    pre_m, post_m = float(j["pre"].mean()), float(j["post"].mean())
    sd = float(d.std(ddof=1)) if n > 1 else 0.0
    t = float(d.mean() / (sd / math.sqrt(n))) if sd > 0 else None
    return dict(
        n_firms=n,
        pre_mean=round(pre_m, 4),
        post_mean=round(post_m, 4),
        abs_delta=round(post_m - pre_m, 4),
        pct_change=round(100 * (post_m - pre_m) / pre_m, 1) if pre_m else None,
        frac_increased=round(float((d > 0).mean()), 3),
        t_stat=round(t, 2) if t is not None else None,
    )


# --------------------------------------------------------------------------- #
# 1. Within-company change over time
# --------------------------------------------------------------------------- #
def within_company(ok: pd.DataFrame) -> pd.DataFrame:
    """One row per firm: how much its language/tone/topic-mix moved over the window.

    Two complementary views of topic change:
      * mean_yoy_shift_cosine  — average *year-to-year* churn (from mine.py's column)
      * start_to_end_cosine    — net drift between the first and last observed year
        (a firm can churn every year yet end where it started, or drift steadily).
    Plus the single biggest rising/falling theme (start→end share change) and the
    tone/readability trend, so the table reads as a per-firm narrative seed.
    """
    rows = []
    for tic, g in ok.groupby("ticker"):
        g = g.sort_values("year")
        first, last = g.iloc[0], g.iloc[-1]
        v0, v1 = first[EMPH].to_numpy(float), last[EMPH].to_numpy(float)
        share_delta = pd.Series(v1 - v0, index=CATS)
        rows.append(dict(
            ticker=tic,
            company_name=first["company_name"],
            sector=first["sector"],
            years_observed=len(g),
            start_year=int(first["year"]),
            end_year=int(last["year"]),
            mean_yoy_shift_cosine=round(float(g["emphasis_shift_cosine"].mean()), 4)
                if g["emphasis_shift_cosine"].notna().any() else None,
            start_to_end_cosine=cosine_distance(v0, v1),
            net_tone_start=round(float(first["net_tone"]), 4),
            net_tone_end=round(float(last["net_tone"]), 4),
            net_tone_delta=round(float(last["net_tone"] - first["net_tone"]), 4),
            flesch_delta=round(float(last["flesch"] - first["flesch"]), 1),
            biggest_rising_theme=share_delta.idxmax(),
            biggest_rising_delta=round(float(share_delta.max()), 4),
            biggest_falling_theme=share_delta.idxmin(),
            biggest_falling_delta=round(float(share_delta.min()), 4),
        ))
    out = pd.DataFrame(rows)
    # Surface the firms whose disclosed emphasis moved most over the window first.
    return out.sort_values("start_to_end_cosine", ascending=False,
                           na_position="last").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 2. Cross-sector variation
# --------------------------------------------------------------------------- #
def sector_fingerprint(ok: pd.DataFrame) -> pd.DataFrame:
    """Sector 'fingerprint': mean emphasis vector + tone + LLM framing, pooled over
    all years. This is the cross-sector view — what each industry's proxies stress
    on average, directly comparable to Part 1's website fingerprints."""
    agg = {c: "mean" for c in EMPH}
    agg.update({"net_tone": "mean", "lm_uncertainty": "mean", "flesch": "mean",
                "llm_concreteness": "mean", "llm_forward_orientation": "mean",
                "ticker": "nunique"})
    fp = ok.groupby("sector").agg(agg).rename(columns={"ticker": "n_firms"})
    fp["top_theme"] = fp[EMPH].idxmax(axis=1).str.replace("emphasis_", "", regex=False)
    return fp.round(4).reset_index()


def sector_year(ok: pd.DataFrame) -> pd.DataFrame:
    """Sector × year mean emphasis for all 10 themes (long-window trend table).

    This is the backbone for both the cross-sector-over-time reading and the
    event windows below; it's emitted in full so a reader can trace any theme in
    any sector year by year without re-running code."""
    sy = (ok.groupby(["sector", "year"])[EMPH]
            .mean()
            .round(4)
            .reset_index()
            .sort_values(["sector", "year"]))
    return sy


# --------------------------------------------------------------------------- #
# 3. External-event windows
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Event:
    """A documented external event + the metric(s) and pre/post windows we test.

    Windows are on *filing year*. Proxies are filed early in the year for the prior
    fiscal year, so an event in year Y first shows up in proxies filed Y or Y+1;
    we therefore leave a one-year buffer (pre ends before the event, post starts
    after it) rather than splitting on the event year itself.
    """
    name: str
    metrics: list[str]
    pre: tuple[int, int]
    post: tuple[int, int]
    rationale: str
    focus_sector: str | None = None   # sector we expect to move most (also reported)


# The events are hypotheses with a clear mechanism, not a fishing expedition; each
# names the theme it should move and the window it should move in. Documented here
# at the point of decision, per repo convention.
EVENTS: list[Event] = [
    Event(
        name="DEI & human-capital disclosure (2020)",
        metrics=["emphasis_diversity_inclusion", "emphasis_people_talent"],
        pre=(2018, 2019), post=(2021, 2022),
        rationale="2020 racial-justice reckoning + SEC's human-capital disclosure "
                  "rule (Reg S-K Item 101(c), adopted Aug 2020, eff. Nov 2020) — "
                  "expect diversity & human-capital language to rise in 2021+ proxies.",
    ),
    Event(
        name="Climate / net-zero wave (2021)",
        metrics=["emphasis_sustainability_environment"],
        pre=(2016, 2018), post=(2022, 2024),
        rationale="Paris ramp, surge of corporate net-zero pledges around COP26 "
                  "(Nov 2021), and 2021 investor pressure on oil & gas (e.g. the "
                  "Engine No.1 / Exxon board fight) — expect environmental language "
                  "to rise, most in Energy.",
        focus_sector="Energy",
    ),
    Event(
        name="COVID-19 (2020)",
        metrics=["lm_uncertainty", "emphasis_people_talent"],
        pre=(2019, 2019), post=(2020, 2021),
        rationale="Pandemic — expect elevated uncertainty language and a workforce "
                  "health/safety (human-capital) emphasis in 2020–21 filings.",
    ),
]


def _window_firm_means(ok: pd.DataFrame, metric: str, lo: int, hi: int) -> pd.Series:
    """Per-firm mean of `metric` over filing years [lo, hi], indexed by ticker."""
    w = ok[(ok["year"] >= lo) & (ok["year"] <= hi)]
    return w.groupby("ticker")[metric].mean()


def event_table(ok: pd.DataFrame) -> pd.DataFrame:
    """For each (event, metric, scope) run the paired pre/post comparison.

    `scope` is 'all firms' plus the event's focus sector when it has one, so we can
    see e.g. that the climate shift is broad but concentrated in Energy."""
    rows = []
    for ev in EVENTS:
        scopes: list[tuple[str, pd.DataFrame]] = [("all", ok)]
        if ev.focus_sector:
            scopes.append((ev.focus_sector, ok[ok["sector"] == ev.focus_sector]))
        for scope_name, sub in scopes:
            for metric in ev.metrics:
                pre = _window_firm_means(sub, metric, *ev.pre)
                post = _window_firm_means(sub, metric, *ev.post)
                stat = paired_shift(pre, post)
                rows.append(dict(
                    event=ev.name,
                    metric=metric,
                    scope=scope_name,
                    pre_window=f"{ev.pre[0]}-{ev.pre[1]}",
                    post_window=f"{ev.post[0]}-{ev.post[1]}",
                    **stat,
                    rationale=ev.rationale,
                ))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Optional plots (graceful if matplotlib absent)
# --------------------------------------------------------------------------- #
def make_plots(ok: pd.DataFrame, out_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log.warning("matplotlib not installed — skipping --plots "
                    "(install it or just use the CSVs).")
        return

    # (a) sustainability_environment share by sector over time
    sy = sector_year(ok)
    fig, ax = plt.subplots(figsize=(8, 5))
    for sector, g in sy.groupby("sector"):
        ax.plot(g["year"], g["emphasis_sustainability_environment"],
                marker="o", label=sector)
    ax.set(title="Sustainability/environment emphasis in proxies, by sector",
           xlabel="Year", ylabel="Mean emphasis share")
    ax.set_ylim(bottom=0)   # honest scale: share data baselined at 0, not auto-zoomed
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_sustainability_by_sector.png", dpi=130)
    plt.close(fig)

    # (b) diversity_inclusion share, all firms, over time
    di = ok.groupby("year")["emphasis_diversity_inclusion"].mean()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(di.index, di.values, marker="o", color="C3")
    ax.set(title="Diversity & inclusion emphasis in proxies (all 50 firms)",
           xlabel="Year", ylabel="Mean emphasis share")
    # Baseline at 0 so the near-flat series isn't visually exaggerated into a "trend"
    # — this is the honest-null finding (#3), and the chart should not contradict it.
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_diversity_over_time.png", dpi=130)
    plt.close(fig)
    log.info("Wrote fig_sustainability_by_sector.png and fig_diversity_over_time.png")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _print_headlines(sector_fp: pd.DataFrame, events: pd.DataFrame,
                     within: pd.DataFrame) -> None:
    """Console digest of the numbers that anchor SUMMARY.md."""
    log.info("\n=== CROSS-SECTOR fingerprint (top theme + net tone) ===")
    for _, r in sector_fp.iterrows():
        log.info("  %-22s top=%-28s net_tone=%+.2f  conc=%.2f",
                 r["sector"], r["top_theme"], r["net_tone"], r["llm_concreteness"])

    log.info("\n=== EXTERNAL EVENTS (paired pre→post) ===")
    for _, r in events.iterrows():
        if r["pre_mean"] is None:
            continue
        log.info("  %-34s %-38s [%s] %.3f→%.3f (%+.0f%%, %.0f%% of firms up, t=%s)",
                 r["event"], f'{r["metric"]} ({r["scope"]})', "",
                 r["pre_mean"], r["post_mean"],
                 r["pct_change"] if r["pct_change"] is not None else float("nan"),
                 100 * r["frac_increased"], r["t_stat"])

    log.info("\n=== WITHIN-COMPANY: 5 biggest topic-mix movers (start→end) ===")
    for _, r in within.head(5).iterrows():
        log.info("  %-5s %-22s drift=%.3f  rising=%s(+%.3f) falling=%s(%.3f)",
                 r["ticker"], r["company_name"], r["start_to_end_cosine"],
                 r["biggest_rising_theme"], r["biggest_rising_delta"],
                 r["biggest_falling_theme"], r["biggest_falling_delta"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Part 2 analysis: cross-sector / "
                                 "over-time / external-event tables from the mined dataset.")
    ap.add_argument("--in-csv", default="data/part2/part2_lived_values.csv", type=Path)
    ap.add_argument("--out-dir", default="data/part2", type=Path)
    ap.add_argument("--plots", action="store_true",
                    help="also write PNG trend charts (requires matplotlib)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ok = load_ok(args.in_csv)

    within = within_company(ok)
    sector_fp = sector_fingerprint(ok)
    sy = sector_year(ok)
    events = event_table(ok)

    within.to_csv(args.out_dir / "analysis_within_company.csv", index=False)
    sector_fp.to_csv(args.out_dir / "analysis_sector_fingerprint.csv", index=False)
    sy.to_csv(args.out_dir / "analysis_sector_year.csv", index=False)
    events.to_csv(args.out_dir / "analysis_events.csv", index=False)

    if args.plots:
        make_plots(ok, args.out_dir)

    _print_headlines(sector_fp, events, within)
    log.info("\nWrote 4 analysis tables to %s", args.out_dir)


if __name__ == "__main__":
    main()
