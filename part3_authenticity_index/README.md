# Part 3 — Organizational Authenticity Index

Combines Part 1 (what each firm **says** it values — the LLM-coded theme profile of
its archived "About/values" page) and Part 2 (what its mandatory disclosures
**suggest** it prioritizes — the emphasis profile of its proxy statement) into a
single measure of **say–do alignment**, varying across firms and over time. Both
sides live on the *same 10-category taxonomy*, which is what makes the comparison
clean.

## Pipeline

```
data/part1/part1_stated_values_analyzed.csv   (theme_categories: {category: salience})
data/part2/part2_lived_values.csv             (emphasis_<category>: shares summing to 1)
        │
        ▼
build_index.py    # harmonize → 10-dim distributions; match say↔do per company-year;
                  # cosine alignment (raw + peer-relative); company-level summary
        │
        ▼
data/part3/authenticity_index.csv             (one row per scored company-year)
data/part3/authenticity_company_level.csv     (one row per firm)
        │
        ▼
report_index.py   # distributional properties + 3 validity checks (+ --plots)
        │
        ▼
data/part3/authenticity_by_sector.csv  authenticity_by_year.csv  fig_*.png
```

## Run it

```bash
PYTHONPATH=. python -m part3_authenticity_index.build_index
PYTHONPATH=. python -m part3_authenticity_index.report_index --plots
```

No network or API cost — pure pandas/numpy on the committed Part 1/Part 2 outputs.

---

## Operationalizing "alignment" (the central judgment call)

Authenticity = **how similar a firm's stated theme profile is to its disclosed
emphasis profile**, on the shared 10-category space. Three deliberate choices:

### 1. Compare profile *shape*, not *levels* — via cosine
The two genres have very different baselines: a marketing-toned website vs. a
governance/compensation-heavy proxy. Absolute emphasis levels therefore aren't
comparable, but the **relative mix of themes** is. Cosine similarity compares
direction (the mix) and ignores magnitude — the right tool. We L1-normalize both
sides to distributions on the 10-simplex first (Part 1 salience dict → 10-vector,
absent categories = 0, normalized; Part 2 shares already sum to 1).

### 2. Two measures: raw, and peer-relative (**primary**)
- **`align_cosine_raw`** = cosine(stated, disclosed). Simple and interpretable, but
  partly measures **genre**: every firm's proxy is financial/governance-heavy and
  every firm's website is customer/innovation-toned, so raw alignment is inflated or
  deflated by the *document type*, not just the firm. (Its sample mean ≈ 0.48.)
- **`align_cosine_centered`** = cosine(stated − mean_stated_year, disclosed −
  mean_disclosed_year) — **the headline measure.** We subtract each year's
  cross-firm mean profile from each side and compare the *deviations*. This removes
  the common genre/year baseline and asks the question we actually care about:

  > *The themes this firm stresses **more than its peers** in what it SAYS — does it
  > also stress them more than its peers in what it DISCLOSES?*

  Range [−1, +1]: **+1** = a firm's distinctive say-emphasis and distinctive
  do-emphasis point the same way (authentic positioning); **~0** = unrelated;
  **negative** = it talks up the very themes it de-emphasizes in disclosure (a
  say–do *inversion*). We also publish **`authenticity_score`** = `(cos+1)/2×100`
  (0–100) for non-technical readers, and a company-level **`centroid_cosine_*`**
  (cosine of the firm's mean stated vs mean disclosed profile) that is robust to a
  single noisy year. *Validity check V3 confirms centering re-orders firms (raw vs
  centered rank corr ≈ 0.36), i.e. raw alignment really was partly document-type.*

### 3. Vary across firms **and** over time → score per company-year
Part 2 is near-complete annually; Part 1 (opportunistic web archive) is sparser. A
stated profile is matched to a disclosure year as:
- **`same_year`** — both observed that year (primary; 300 of 375 scored years);
- **`carried_forward`** — no stated profile that year, so carry forward the most
  recent *prior* stated profile (value statements are sticky — they persist on a
  site until rewritten). Flagged via `stated_year_used` + `stated_lag_years`, never
  silently. Years with no same-or-prior stated profile are left **unscored** (an
  explicit gap), as are the two firms Part 1 could never theme (AAPL, BRK.B —
  too-thin About pages). Net: **375 company-years across 48 firms.**

---

## Output schema

**`authenticity_index.csv`** — one row per scored company-year:

| column | meaning |
|---|---|
| `ticker`, `company_name`, `sector`, `year` | keys |
| `match_type` | `same_year` \| `carried_forward` (stated-profile provenance) |
| `stated_year_used`, `stated_lag_years` | which Part 1 year supplied the stated profile, and the lag |
| `align_cosine_raw` | raw profile cosine (genre-confounded; for contrast) |
| **`align_cosine_centered`** | **primary measure** — peer-relative say↔do alignment, [−1,1] |
| `authenticity_score` | `align_cosine_centered` rescaled to 0–100 (reader-friendly) |
| `top_say`, `top_do` | dominant stated / disclosed theme that year |
| `largest_overclaim`, `overclaim_gap` | theme most *talked up* vs disclosed (absolute share gap) |
| `largest_underclaim`, `underclaim_gap` | theme most *disclosed* vs talked up |

> Note: `over/under-claim` are on **raw** distributions, so they're dominated by
> genre (websites talk community/innovation; proxies talk money) and are best read
> as *descriptive colour*, not the authenticity signal — that's the centered cosine.

**`authenticity_company_level.csv`** — one row per firm: `n_years_scored`,
`mean_authenticity_score`, `mean_cosine_centered` (+ `sd`), `mean_cosine_raw`,
`centroid_cosine_raw`, `centroid_cosine_centered`. Sorted most→least authentic.

---

## Distributional properties (`report_index.py`)
- **Company-year primary measure:** mean **0.07**, sd **0.33**, range **[−0.79, 0.80]**;
  **44%** of company-years are negative (a say–do inversion relative to peers). The
  distribution is roughly symmetric, slightly right-skewed (`fig_authenticity_hist.png`).
- **By sector** (mean centered cosine): **Technology +0.17 > Consumer Disc. +0.12 ≈
  Energy +0.11 > Financials −0.00 > Healthcare −0.03**. Tech firms' stated and
  disclosed distinctive emphases line up best; Healthcare's diverge most.
- **Over time:** a clear **upward trend**, mean alignment rising from **−0.02 (2016)
  to +0.20 (2024)** (`fig_authenticity_over_time.png`) — websites and proxies have
  *converged* thematically, consistent with both genres adopting
  stakeholder/ESG/human-capital language over the window.

## Validity checks
- **V1 — face validity.** Most authentic: **Lowe's, TJX, Occidental, Amex, IBM**;
  least: **UnitedHealth, Abbott, BlackRock, Citigroup, ConocoPhillips**. The
  bottom-ranked **UnitedHealth** brands itself on *innovation/technology* while its
  proxy is distinctively *financial/shareholder*-tilted vs peers — a firm whose
  say–do gap is much-discussed publicly landing lowest is a reassuring sign.
- **V2 — stability.** Between-firm sd (0.255) exceeds within-firm sd (0.209): **~60%
  of the variance is between firms**, so the index is a reasonably **stable firm
  trait**, not yearly noise — yet with enough within-firm movement to function as a
  *time-varying* measure (which the brief requires).
- **V3 — centering earns its keep.** Raw vs centered firm-mean rank correlation is
  only **~0.36**, so removing the genre/year baseline materially re-orders firms —
  evidence the raw measure was substantially capturing document type.

## Known limitations & threats to validity
1. **Residual genre confound.** Centering removes the *average* genre baseline but
   not genre × firm interactions (e.g. a firm whose business genuinely is finance
   will look financial in both genres for real reasons). Alignment is *relative*,
   never absolute.
2. **Part 1 sparsity + carry-forward.** 75 of 375 scored years reuse a prior
   stated profile (max lag flagged per row); this assumes value statements are
   sticky. Where the website changed silently between archive captures, a carried
   profile is stale. AAPL and BRK.B are unscored entirely (Part 1 could not theme
   them). Coverage is honest, not complete.
3. **Two measurement layers, each imperfect.** The stated side is an *LLM coding* of
   page text (gpt-4o-mini, 0–1 salience) and the disclosed side is a *lexicon* share
   vector — both are reproducible measurements of *vocabulary/theme emphasis*, not
   ground-truth values. Errors in either propagate into alignment.
4. **A disclosure is the firm's own account, not its behavior.** Part 2 is "lived
   values *as disclosed*," so the index measures *rhetorical* say–do consistency, not
   whether the firm actually acts on either. High alignment ≠ virtuous; it means the
   talk and the disclosed emphasis agree.
5. **Thin per-year cohorts early on.** Centering uses cross-firm year means; with as
   few as 26 firms in 2016, early-year baselines are noisier than late-year ones.
6. **Direction is symmetric.** Cosine can't tell "raised disclosure to match talk"
   from "quietly dropped a claim"; the over/under-claim columns add some directional
   colour but the headline index is symmetric.

## Assumptions & what we'd do differently with more time
- **Assumed** the 10-category taxonomy is an adequate shared space and that L1
  profiles are the right harmonization. With more time: validate/expand the Part 2
  lexicons against hand-labelled filings, and bootstrap confidence intervals on each
  firm's score (the sd column is a start).
- **Assumed** carry-forward is preferable to dropping years; a sensitivity run
  restricted to `same_year` only is one flag away (`match_type` is in the data).
- Would add an LLM-based *commitment-substance* dimension (Part 2 already has
  `llm_concreteness` / `llm_forward_orientation`) so authenticity blends *thematic*
  alignment with *whether the talk is concrete* — sketched as a Part 4 direction.

## How it scales
Pure pandas/numpy over the Part 1/Part 2 outputs — nothing is hard-coded to 50.
Run the full S&P 500 through Parts 1–2 and this module produces the index unchanged;
the centering baselines simply get more stable with more firms per year.
