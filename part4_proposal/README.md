# Part 4 — Exploratory Proposal: Is rising say–do alignment *authenticity*, or *herding*?

## The proposal (what I chose to investigate, and why)

Part 3 produced an upbeat headline: peer-relative say↔do alignment **rose across the
sample from ≈ −0.02 (2016) to +0.20 (2024)** — firms look like they're increasingly
"walking their talk." The most interesting thing I can do with that result is **not
celebrate it — it's try to break it.**

There is a well-known alternative explanation from organizational theory:
**institutional isomorphism** (DiMaggio & Powell, 1983). Over 2016–2024 the entire
corporate field adopted a shared stakeholder / ESG / human-capital vocabulary. If
*every* firm drifts onto the *same* script in both what it **says** (websites) and what
it **discloses** (proxies), then the two genres mechanically line up — alignment rises —
**without any individual firm genuinely closing its own authenticity gap.** That would
be a legitimacy *bandwagon*, not authenticity.

So Part 4 asks: **how much of Part 3's rise is real per-firm gap-closing, and how much
is just everyone converging on a common template?** This is the most honest possible
follow-on — it stress-tests my own marquee finding rather than decorating it.

## Method (`convergence.py`)

The test is **cross-firm dispersion over time**. For each year I take every firm's
profile (the same L1-normalized 10-category vectors Part 3 uses — imported directly
from `part3_authenticity_index.build_index`, so the definitions can't drift) and measure
how *spread out* firms are around that year's average profile:

- **`mean_l2_to_centroid`** — average Euclidean distance of firms to the year centroid.
  This is the headline dispersion metric, and it does **double duty**: it is *exactly*
  the average magnitude of the deviation vectors that Part 3's **centered** cosine runs
  on (Part 3 centers each side on its year mean). So a falling value is both
  convergence evidence *and* a direct statement about Part 3's signal strength.
- **`mean_cosdist_to_centroid`** — average cosine distance to the centroid (shape-only
  spread; complements L2).

**Falling dispersion ⇒ the field is converging (herding).** I fit a hand-rolled OLS
trend (slope + t-stat, no scipy — matching Part 2's convention) and report start-vs-end.

**Disentangling mechanical from genuine.** Convergence inflates *raw* alignment
mechanically (both genres slide toward one shared centroid, so `cosine(say, do)` climbs
for everyone) but does **not** inflate the *centered* measure (centering removes the
common drift). So I plot Part 3's **raw and centered** alignment by year *against* the
dispersion trend (`fig_convergence_vs_alignment.png`) — the gap between the two curves
*is* the herding artifact.

**Which themes converged?** I also track each category's cross-firm SD per year and
compare an early window (≤2018) to a late one (≥2022), on both the stated and disclosed
sides (`convergence_by_category.csv`).

```bash
PYTHONPATH=. python -m part4_proposal.convergence --plots
```
Pure pandas/numpy on the committed Part 1/2/3 outputs — no network, no API cost.

---

## What I found

### 1. Disclosures converged — robustly. Websites converged — weakly.
Cross-firm dispersion (mean L2 to the year centroid):

| side | 2016 | 2024 | OLS slope/yr | t (dof=7) |
|---|---|---|---|---|
| **Disclosed** (proxies, dense, ~49 firms/yr) | 0.159 | 0.129 | **−0.0036** | **−6.28** |
| **Stated** (websites, sparse, 26–38 firms/yr) | 0.446 | 0.401 | −0.0061 | −2.11 |

Firms' **mandatory disclosure** profiles homogenized strongly and near-monotonically
(t = −6.3, clearly significant). The **website** side also drifted toward the centroid
but the trend is only *suggestive* (t ≈ −2.1, p ≈ 0.07 on 9 points — not significant at
0.05, and the stated side is noisy because Part 1 is sparse early). **So the herding is
real and it lives primarily in disclosure** (`fig_dispersion_over_time.png`).

### 2. Part 3's rise is *partly* mechanical — but its primary measure survives the correction.
Plotting alignment against the falling dispersion (`fig_convergence_vs_alignment.png`):

- **Raw alignment rose 0.40 → 0.54.** As firms converge on a shared template, this
  climbs for everyone. **A meaningful chunk of "raw" say–do agreement is herding, not
  authenticity** — exactly the confound Part 3 warned `align_cosine_raw` carried.
- **Centered alignment (Part 3's *primary* measure) rose −0.02 → +0.20.** Centering
  nets out the common drift, so this rise is **not** mechanically produced by
  convergence. **This vindicates the central Part 3 design choice:** peer-relative
  centering is precisely the correction that strips the herding artifact, and alignment
  *still* rose after it — so the gain reflects genuine relative-positioning consistency,
  not just everyone reciting the same script.
- **…with one honest caveat back to Part 3.** The centered cosine is computed *on* the
  deviation vectors whose magnitude is the dispersion that's shrinking (−19% disclosed
  over the window). So the late-window centered numbers rest on a **fainter, noisier
  signal**. Confidence in the *direction* (still rising after centering) goes up;
  confidence in the precise *late-year levels* goes down. This is a concrete, earned
  refinement of a Part 3 limitation, not a hand-wave.

### 3. The twist: convergence is theme-specific — and **sustainability is where firms *diverged* most.**
The naive isomorphism story predicts the *ESG* themes (sustainability, diversity)
converge most. **The data say almost the opposite.** Change in cross-firm SD,
early (≤2018) → late (≥2022) (`fig_theme_convergence.png`):

| theme | disclosed Δ | stated Δ | reading |
|---|---|---|---|
| financial_growth_shareholder | **−33%** | −16% | homogenized |
| people_talent | **−32%** | −26% | homogenized |
| quality_excellence | −25% | −28% | homogenized |
| integrity_ethics | −22% | −29% | homogenized |
| diversity_inclusion | −6% | −19% | mild homogenize |
| community_social_impact | **+36%** | −11% | mixed |
| innovation_technology | +1% | **+17%** | diverged (stated) |
| **sustainability_environment** | **+59%** | **+30%** | **diverged (both)** |

Two readings fall out, both more interesting than "everyone adopted ESG-speak":

- **Convergence concentrates on "table-stakes" and *regulated* themes.** The biggest
  disclosure homogenization is in **financial/shareholder** (proxies are universally
  financial) and **people_talent**. The people_talent convergence coincides with the
  **SEC's human-capital disclosure rule** (Reg S-K Item 101(c), effective Nov 2020),
  which forced essentially every registrant to add human-capital language — a
  *regulatory* convergence driver, not a voluntary values bandwagon. (Coincidence in
  timing; I flag it as a plausible mechanism, not a proven cause.)
- **Sustainability is a *differentiation* axis, not a convergence one.** Cross-firm
  spread on `sustainability_environment` **grew ~59% in disclosure and ~30% on
  websites** — firms became *more* unalike here. This matches real-world **ESG
  polarization** over the window (the post-2022 anti-ESG backlash; Energy leaning out
  while Tech/Consumer lean in) and is consistent with Part 2's finding that the
  climate-language shift was strong but highly *heterogeneous*. So the one theme most
  associated with "corporate values talk" is precisely where firms are staking out
  *different* positions, not herding.

**Net finding:** Part 3's optimistic rise is *partly* an artifact of field-wide herding
(it inflates the raw measure), but the peer-relative measure was built to remove exactly
that and the gain survives — while the herding itself is driven by financial/regulated
themes, and **sustainability runs the other way, becoming a fault line of corporate
self-presentation.** That is a genuinely non-obvious, two-sided result.

---

## Output schema
**`convergence_by_year.csv`** — one row per year: `do_n_firms`,
`do_mean_l2_to_centroid`, `do_mean_cosdist_to_centroid` (disclosed dispersion);
`say_*` equivalents (stated); `n`, `raw_alignment`, `centered_alignment` (Part 3
by-year bridge).
**`convergence_by_category.csv`** — one row per (side, theme): `sd_early_2016_2018`,
`sd_late_2022_2024`, `delta`, `pct_change`. Negative `pct_change` = firms converged on
that theme; positive = diverged. Sorted most-converged first within each side.

## Assumptions
- **Dispersion = distance to the year centroid** is an adequate proxy for "how alike
  are firms." (Mean pairwise distance would give the same ordering; centroid distance
  is cheaper and ties directly to Part 3's centering.)
- **Genuine observations only.** Dispersion uses real Part 1 themed years (no Part 3
  carry-forward), so website convergence isn't a fixture of reused profiles.
- The 10-category taxonomy is a fair shared space (inherited assumption from Parts 1–3).

## Known limitations / threats
1. **Convergence ≠ proof of mimicry.** Firms could homogenize because they face a *real*
   common shock (a regulation, a recession), not because they imitate each other. The
   SEC human-capital rule is itself such a non-mimetic driver. I show convergence and
   offer mechanisms; I don't claim to identify imitation per se.
2. **Stated-side trend is weak.** With 26–38 firms/yr and 9 noisy points, the website
   convergence is only suggestive (t ≈ −2.1). The robust half of the story is disclosure.
3. **Compositional metric.** Shares sum to 1, so a theme that grows mechanically shrinks
   others; the per-theme deltas are relative, not absolute "attention."
4. **Centroid noise early.** 2016 has the fewest firms, so the early dispersion baseline
   is the least precise — which, if anything, *understates* the true decline.

## What I'd do with more time
- **A proper isomorphism test:** decompose convergence into mimetic (peer imitation),
  coercive (regulation), and normative (consultants/raters) channels — e.g. event-study
  the people_talent collapse around the Nov-2020 SEC rule date, and test whether firms
  move toward their *sector* centroid (mimetic) faster than the *grand* centroid.
- **Bootstrap CIs** on the yearly dispersion so the trend has error bars, not just a slope.
- **Re-express Part 3's late-window scores** with a signal-to-noise flag derived from the
  deviation magnitudes computed here, so readers know which company-years rest on a thin
  peer-relative signal.

## How it scales
Pure pandas/numpy over the Part 1/2/3 outputs; nothing hard-coded to 50. Run the full
S&P 500 through Parts 1–3 and this module produces the convergence diagnostics unchanged
— with *more* firms per year, the dispersion trends only get more precise.
