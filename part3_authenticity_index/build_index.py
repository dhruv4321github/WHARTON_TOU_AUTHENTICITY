"""
Part 3 — Organizational Authenticity Index: build the measure.

Authenticity here = the alignment between what a firm SAYS it values (Part 1, the
LLM-coded theme profile of its archived "About/values" page) and what its mandatory
disclosures SUGGEST it prioritizes (Part 2, the emphasis profile of its proxy
statement). Both sides are expressed on the SAME 10-category taxonomy, which is the
whole reason a clean comparison is possible.

--------------------------------------------------------------------------------
OPERATIONALIZING "ALIGNMENT" (the central judgment call the brief asks us to make)
--------------------------------------------------------------------------------
We compare PROFILE SHAPE, not levels. The two genres have very different baselines
(a marketing-toned website vs. a governance/compensation-heavy proxy), so absolute
emphasis levels aren't comparable — but the *relative* mix of themes is. Cosine
similarity is the natural shape comparison (scale-invariant, ignores magnitude),
and we implement it two ways:

  (1) RAW cosine(stated_profile, disclosed_profile).
      Simple and interpretable, but partly measures GENRE: every firm's proxy is
      financial/governance-heavy and every firm's website is customer/innovation-
      toned, so raw alignment is inflated/deflated by the document type, not just
      the firm.

  (2) PEER-RELATIVE ("centered") cosine  <-- PRIMARY MEASURE.
      Subtract each year's cross-firm MEAN profile from each side, then take the
      cosine of the two deviation vectors. This removes the common genre/year
      baseline and asks the question we actually care about:
        "The themes this firm stresses MORE THAN ITS PEERS in what it SAYS —
         does it also stress them more than its peers in what it DISCLOSES?"
      Centered cosine ranges [-1, 1]: +1 = a firm's distinctive say-emphasis and
      its distinctive do-emphasis point the same way (authentic positioning);
      ~0 = unrelated; negative = it talks up the very themes it de-emphasizes in
      disclosure (a say-do inversion). We also publish a 0–100 rescaling
      ((cos+1)/2*100) for non-technical readers.

--------------------------------------------------------------------------------
VARYING ACROSS FIRMS AND OVER TIME (also required)
--------------------------------------------------------------------------------
We score per COMPANY-YEAR. Part 2 is near-complete annually; Part 1 (opportunistic
web archive) is sparser, so a stated profile is matched to a disclosure year as:
  * same_year       — both observed in the same calendar year (primary, 300 yrs);
  * carried_forward — no stated profile that year, so we carry forward the most
                      recent PRIOR stated profile (values statements are sticky;
                      they persist on a site until rewritten). Flagged with
                      `stated_year_used` + `stated_lag_years`, never silently.
Years with no same-or-prior stated profile are left unscored (an explicit gap).
Time variation then comes from BOTH sides drifting; cross-firm variation is the
firm's distinctive positioning. We also emit a company-level summary.

Inputs : data/part1/part1_stated_values_analyzed.csv   (theme_categories dict)
         data/part2/part2_lived_values.csv             (emphasis_<cat> shares)
Outputs: data/part3/authenticity_index.csv             (one row per scored co-year)
         data/part3/authenticity_company_level.csv      (one row per firm)

    PYTHONPATH=. python -m part3_authenticity_index.build_index
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from part1_stated_values.analyze import TAXONOMY

log = logging.getLogger("part3.build")

CATS = list(TAXONOMY.keys())                       # fixed 10-category order
EMPH = [f"emphasis_{c}" for c in CATS]             # Part 2 column names


# --------------------------------------------------------------------------- #
# Load + harmonize both sides to 10-dim distributions on the shared taxonomy
# --------------------------------------------------------------------------- #
def _l1(vec: np.ndarray) -> np.ndarray | None:
    """L1-normalize a non-negative vector to a distribution summing to 1."""
    s = vec.sum()
    return vec / s if s > 0 else None


def load_stated(path: Path) -> pd.DataFrame:
    """Part 1 → one row per themed company-year with a stated distribution.

    `theme_categories` is a dict {category: salience 0-1}; we lay it onto the fixed
    10-vector (absent categories = 0) and L1-normalize so it's a distribution
    directly comparable to Part 2's share vector. Empty-theme rows are dropped (they
    carry no stated signal) — an explicit non-score, consistent with the project's
    no-silent-fill rule.
    """
    df = pd.read_csv(path)
    rows = []
    for _, r in df[df.coverage_status == "ok"].iterrows():
        try:
            themes = json.loads(r.theme_categories) if isinstance(r.theme_categories, str) else {}
        except (json.JSONDecodeError, TypeError):
            themes = {}
        if not themes:
            continue
        vec = np.array([float(themes.get(c, 0.0)) for c in CATS])
        dist = _l1(vec)
        if dist is None:
            continue
        rows.append(dict(ticker=r.ticker, company_name=r.company_name, sector=r.sector,
                         year=int(r.year), **{f"say_{c}": dist[i] for i, c in enumerate(CATS)}))
    out = pd.DataFrame(rows)
    log.info("Stated (Part 1): %d themed company-years across %d firms.",
             len(out), out.ticker.nunique())
    return out


def load_disclosed(path: Path) -> pd.DataFrame:
    """Part 2 → one row per usable company-year with a disclosed distribution
    (the emphasis shares already sum to 1)."""
    df = pd.read_csv(path)
    ok = df[df.coverage_status == "ok"].copy()
    for c in EMPH:
        ok[c] = pd.to_numeric(ok[c], errors="coerce").fillna(0.0)
    out = ok[["ticker", "company_name", "sector", "year"] + EMPH].rename(
        columns={f"emphasis_{c}": f"do_{c}" for c in CATS})
    log.info("Disclosed (Part 2): %d usable company-years across %d firms.",
             len(out), out.ticker.nunique())
    return out


# --------------------------------------------------------------------------- #
# Similarity helpers
# --------------------------------------------------------------------------- #
def cosine(a: np.ndarray, b: np.ndarray) -> float | None:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return None
    return float(np.dot(a, b) / (na * nb))


def year_means(df: pd.DataFrame, cols: list[str]) -> dict[int, np.ndarray]:
    """Cross-firm mean profile per year (the centering baseline for measure #2)."""
    return {int(y): g[cols].mean().to_numpy(float) for y, g in df.groupby("year")}


# --------------------------------------------------------------------------- #
# Match stated→disclosed per company-year (same-year, else carry forward)
# --------------------------------------------------------------------------- #
def build_panel(stated: pd.DataFrame, disclosed: pd.DataFrame) -> pd.DataFrame:
    say_cols = [f"say_{c}" for c in CATS]
    do_cols = [f"do_{c}" for c in CATS]
    say_year_mean = year_means(stated, say_cols)
    do_year_mean = year_means(disclosed, do_cols)

    # index stated rows by (ticker, year) and the sorted list of themed years/firm
    stated_idx = {(r.ticker, int(r.year)): r for _, r in stated.iterrows()}
    themed_years: dict[str, list[int]] = {}
    for t, y in stated_idx:
        themed_years.setdefault(t, []).append(y)
    for t in themed_years:
        themed_years[t].sort()

    rows = []
    for _, d in disclosed.iterrows():
        tic, yr = d.ticker, int(d.year)
        # pick the stated profile: same year if present, else most recent prior year
        src_year = None
        if (tic, yr) in stated_idx:
            src_year = yr
        else:
            prior = [y for y in themed_years.get(tic, []) if y < yr]
            if prior:
                src_year = prior[-1]
        if src_year is None:
            continue  # no same-or-prior stated profile → unscored (explicit gap)

        s = stated_idx[(tic, src_year)]
        say = np.array([s[f"say_{c}"] for c in CATS])
        do = np.array([d[f"do_{c}"] for c in CATS])

        # (1) raw profile cosine
        raw = cosine(say, do)
        # (2) peer-relative cosine: deviation from each side's own-year cross-firm mean
        say_dev = say - say_year_mean[src_year]
        do_dev = do - do_year_mean[yr]
        centered = cosine(say_dev, do_dev)

        # interpretability: where do say and do diverge most? (on raw distributions)
        gap = pd.Series(say - do, index=CATS)   # + = says more than discloses
        rows.append(dict(
            ticker=tic, company_name=d.company_name, sector=d.sector, year=yr,
            match_type="same_year" if src_year == yr else "carried_forward",
            stated_year_used=src_year, stated_lag_years=yr - src_year,
            align_cosine_raw=round(raw, 4) if raw is not None else None,
            align_cosine_centered=round(centered, 4) if centered is not None else None,
            authenticity_score=round(100 * (centered + 1) / 2, 1) if centered is not None else None,
            top_say=CATS[int(np.argmax(say))],
            top_do=CATS[int(np.argmax(do))],
            largest_overclaim=gap.idxmax(),     # talked up >> disclosed
            overclaim_gap=round(float(gap.max()), 4),
            largest_underclaim=gap.idxmin(),    # disclosed >> talked up
            underclaim_gap=round(float(gap.min()), 4),
        ))
    panel = pd.DataFrame(rows).sort_values(["sector", "ticker", "year"]).reset_index(drop=True)
    log.info("Scored %d company-years (%d same-year, %d carried-forward) across %d firms.",
             len(panel), (panel.match_type == "same_year").sum(),
             (panel.match_type == "carried_forward").sum(), panel.ticker.nunique())
    return panel


# --------------------------------------------------------------------------- #
# Company-level summary (for ranking + validity)
# --------------------------------------------------------------------------- #
def company_level(panel: pd.DataFrame, stated: pd.DataFrame,
                  disclosed: pd.DataFrame) -> pd.DataFrame:
    """One row per firm: average over its scored years PLUS a centroid score
    (cosine of its mean stated profile vs its mean disclosed profile), which is
    robust to a single noisy year."""
    say_cols = [f"say_{c}" for c in CATS]
    do_cols = [f"do_{c}" for c in CATS]
    say_centroid = stated.groupby("ticker")[say_cols].mean()
    do_centroid = disclosed.groupby("ticker")[do_cols].mean()
    # grand means for centering the centroids (cross-firm, pooled over years)
    say_grand = stated[say_cols].mean().to_numpy(float)
    do_grand = disclosed[do_cols].mean().to_numpy(float)

    rows = []
    for tic, g in panel.groupby("ticker"):
        rec = dict(
            ticker=tic, company_name=g.company_name.iloc[0], sector=g.sector.iloc[0],
            n_years_scored=len(g),
            mean_authenticity_score=round(g.authenticity_score.mean(), 1),
            mean_cosine_centered=round(g.align_cosine_centered.mean(), 4),
            sd_cosine_centered=round(g.align_cosine_centered.std(ddof=1), 4) if len(g) > 1 else None,
            mean_cosine_raw=round(g.align_cosine_raw.mean(), 4),
        )
        if tic in say_centroid.index and tic in do_centroid.index:
            sc = say_centroid.loc[tic].to_numpy(float)
            dc = do_centroid.loc[tic].to_numpy(float)
            rec["centroid_cosine_raw"] = round(cosine(sc, dc), 4)
            cc = cosine(sc - say_grand, dc - do_grand)
            rec["centroid_cosine_centered"] = round(cc, 4) if cc is not None else None
        rows.append(rec)
    out = pd.DataFrame(rows).sort_values("mean_cosine_centered", ascending=False).reset_index(drop=True)
    return out


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Build the Part 3 authenticity index.")
    ap.add_argument("--part1", default="data/part1/part1_stated_values_analyzed.csv", type=Path)
    ap.add_argument("--part2", default="data/part2/part2_lived_values.csv", type=Path)
    ap.add_argument("--out-dir", default="data/part3", type=Path)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    stated = load_stated(args.part1)
    disclosed = load_disclosed(args.part2)
    panel = build_panel(stated, disclosed)
    firms = company_level(panel, stated, disclosed)

    panel.to_csv(args.out_dir / "authenticity_index.csv", index=False)
    firms.to_csv(args.out_dir / "authenticity_company_level.csv", index=False)
    log.info("\nWrote authenticity_index.csv (%d rows) and authenticity_company_level.csv (%d firms) to %s",
             len(panel), len(firms), args.out_dir)


if __name__ == "__main__":
    main()
