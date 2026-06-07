# Organizational Authenticity & Corporate Value Alignment

A scoped proof-of-concept measuring the gap between what large firms **say** they
value and what their disclosures **suggest** they actually prioritize. Run on 50
of the S&P 500 (10 each from Technology, Financials, Healthcare, Consumer
Discretionary, Energy; Jan-2024 composition) over 2016–2024, with methods built
to scale to the full index.

## Repository layout

```
part1_stated_values/        # Part 1 — what firms SAY (Wayback "About Us" pages)
  cdx.py                    #   CDX discovery + per-year snapshot selection
  extract.py                #   fetch + boilerplate-stripped text + change detect
  collect.py                #   orchestrator → structured dataset + coverage report
  analyze.py                #   LLM theme/linguistic-shift pass (value taxonomy)
  README.md
part2_lived_values/         # Part 2 — what firms DISCLOSE (proxy statements via EDGAR)
  edgar.py                  #   SEC EDGAR DEF 14A resolver + download (cached)
  extract_filing.py         #   filing HTML/txt → clean text
  lexicons.py               #   category lexicons (= Part 1 taxonomy) + LM tone loader
  mine.py                   #   classical metrics (+ LLM layer) → structured dataset
  analysis.py               #   over-time / cross-sector / external-event tables
  README.md
common/
  llm.py                    # shared, provider-swappable LLM client (OpenAI)
part3_authenticity_index/   # Part 3 — say-vs-do alignment measure
  build_index.py            #   harmonize Part1/Part2 → say↔do alignment (raw + centered)
  report_index.py           #   distribution + validity checks + plots
  README.md
part4_proposal/             # Part 4 — exploratory: is rising alignment real or herding?
  convergence.py            #   cross-firm dispersion over time + Part3 raw/centered bridge
  README.md
config/
  companies.py              # the 50-company sample + value-page seeds (shared)
data/                       # output datasets (created at runtime)
requirements.txt
```

## How the parts connect

- **Part 1 — Stated values.** Longitudinal value *language* per firm (this is
  the "say"). ✅ collected + LLM-themed for all 50 (328/450 usable); `SUMMARY.md` done.
- **Part 2 — Lived values.** Text mining of **proxy statements (DEF 14A) via SEC
  EDGAR** — the firm's own mandatory disclosure of governance, pay, board
  diversity, and human-capital/ESG oversight. ✅ run for all 50 (442/450 usable, 98%);
  emphasis vector shares Part 1's taxonomy; LLM commitment layer
  (`concreteness`/`forward_orientation`) run on all 442 usable filings; `SUMMARY.md`
  written. (Chosen over voluntary ESG/sustainability reports for coverage and
  sourcing reliability.)
- **Part 3 — Authenticity index.** ✅ An explicit operationalization of *alignment*
  between Part 1 and Part 2 on the shared 10-category space: a **peer-relative
  (centered) cosine** between each firm's stated theme profile and its disclosed
  emphasis profile, scored per company-year (375 years / 48 firms) and per firm.
  Varies across firms and over time (alignment rises 2016→2024; Tech highest,
  Healthcare lowest), with distributional summary + 3 validity checks; `SUMMARY.md` done.
- **Part 4 — Proposal.** ✅ Stress-tests Part 3's own headline (alignment rose
  2016→2024): is it genuine per-firm gap-closing or *institutional herding*? Measures
  cross-firm profile **dispersion** over time. Finding: disclosures converged robustly
  (t≈−6.3) so the *raw* alignment rise is partly mechanical — but Part 3's *peer-relative*
  measure (built to strip exactly that) still rises, vindicating the design; and the
  twist, **sustainability is where firms *diverged* most** (cross-firm spread +59%),
  a fault line, not a bandwagon. `README.md` + `SUMMARY.md` done.

## Deliverables — requirement coverage

*Each required sub-task from the brief, mapped to a one-line summary of how it was met,
a link to where the full reasoning/detail lives, and a concrete example taken directly
from the committed output data — every number/quote below is real (file + row), nothing
invented.*

### Part 1 — Stated Values ([detail → `part1_stated_values/README.md`](part1_stated_values/README.md))

| Brief requirement | How we did it (brief) | Real example (from `data/part1/`) |
|---|---|---|
| Criteria for the correct page; rule for missing snapshots / redirects | "Probe, don't guess": query CDX for each candidate URL, keep the one covering the most of the 9 years; a missing year → explicit `no_snapshot_in_year` row (never interpolated); redirects → keep `statuscode:200` and let the fetcher follow the capture-time chain. *(README §"Key decisions" 1–3)* | **Microsoft** resolved to `source_url = microsoft.com/en-us/about`. **Apple** is archived in only **2 of 9** years → the other 7 rows are emitted as `no_snapshot_in_year` (counted, not hidden). |
| Extract visible body text; strip nav/footer/boilerplate | trafilatura (recall-favoured) + BeautifulSoup fallback on the raw `id_` capture; pages under 80 chars flagged `thin_text`. *(README §4)* | **Microsoft** 2024 cleaned text begins *"Our mission is to empower every person and every organization on the planet to achieve more"* (`text_char_len = 1209`). **Broadcom** 2019–21 extracted only **8 chars** → flagged `thin_text`, excluded from content. |
| LLM analysis: (a) changed-from-prior, (b) theme categories, (c) linguistic shifts | (a) is deterministic (normalized-hash + difflib < 0.95), kept *out* of the LLM; (b) 10-category multi-label salience 0–1; (c) a shift note is only generated when (a) flagged a change. *(README §5 + §"Analysis layer"; taxonomy justified in `analyze.py`)* | **Nike** 2018: similarity to 2017 = **0.013 → `changed_from_prior = True`**; `theme_categories = {innovation_technology 1.0, people_talent 0.5, diversity_inclusion 0.5, sustainability_environment 0.5, community_social_impact 0.5, …}`; `analyst_notes = "new emphasis on community impact and sustainability, while the previous focus on inspiration and innovation has shifted to a broader mission statement."` |
| Structured dataset, ≥ the 8 required columns | One row per company-year with all 8 required columns + provenance/QA columns. *(README §"Output schema" → `part1_stated_values_analyzed.csv`)* | **328 / 450** company-years usable (73%); the Microsoft-2024 and Nike-2018 rows above are live examples. |

### Part 2 — Lived Values ([detail → `part2_lived_values/README.md`](part2_lived_values/README.md))

| Brief requirement | How we did it (brief) | Real example (from `data/part2/`) |
|---|---|---|
| Changes in language, tone, topic emphasis over time within companies | Per-firm: YoY emphasis-shift cosine, start→end cosine, Loughran-McDonald-style net-tone trend, biggest rising/falling theme. *(→ `analysis_within_company.csv`)* | **ExxonMobil** 2016→2024: biggest **rising** theme = `sustainability_environment` (+0.021 share), biggest **falling** = `financial_growth_shareholder` (−0.040); net tone −0.045. |
| Cross-company & cross-sector variation | Sector "emphasis fingerprint": mean 10-theme share + tone + readability + LLM layer. *(→ `analysis_sector_fingerprint.csv`)* | **Technology** proxies emphasize `diversity_inclusion` most of any sector (**0.221** share); **Financials** is the *only* sector with negative net tone (**−0.201**); **Energy**'s top theme is `people_talent` (0.197). |
| Shifts coinciding with external events | Paired pre/post tests (hand-rolled t-stat + % of firms increasing) on documented events. *(→ `analysis_events.csv`)* | **Climate / net-zero wave (COP26, 2021):** sustainability emphasis 0.041 → 0.098 (**+140%, 98% of firms up, t = 8.8**; Energy subset t = 5.6) — robust. **Honest nulls:** 2020 DEI/human-capital (diversity +2.5%, t = 0.7) and COVID uncertainty (t = 0.9) — no significant shift. |
| Structured dataset, documented schema | One row per filing-year: emphasis vector + tone/readability + LLM commitment layer. *(README §"Output schema" → `part2_lived_values.csv`)* | **442 / 450** filing-years usable (98%). |

### Part 3 — Authenticity Index ([detail → `part3_authenticity_index/README.md`](part3_authenticity_index/README.md))

| Brief requirement | How we did it (brief) | Real example (from `data/part3/`) |
|---|---|---|
| Operationalize "alignment" explicitly + reasoning | Peer-relative ("centered") cosine between a firm's stated theme profile and its disclosed emphasis profile on the shared 10-dim space (raw cosine kept for contrast). *(README §"Operationalizing alignment")* | A firm scores near **+1** when the themes it stresses *more than peers* in words are the same ones it stresses *more than peers* in disclosure. **Amazon** 2018 scores −0.38: it `top_say`s `innovation_technology` but `top_do`s `financial_growth_shareholder`. |
| Vary across companies **and** over time | Scored per company-year (**375 years / 48 firms**). *(README §"Distributional properties" → `authenticity_index.csv`)* | Score range **−0.79 → +0.80**; sample mean rises **−0.02 (2016) → +0.20 (2024)**. |
| Distributional properties + ≥1 validity check | Mean/sd/range + **3** checks (face validity, stability, centering). *(README §"Validity checks"; `report_index.py`)* | Mean **0.07**, sd **0.33**. Face validity: most-aligned **Lowe's (+0.59)**, least **UnitedHealth (−0.42)** — UNH brands on `innovation_technology` but its proxy is distinctively `financial_growth_shareholder`. |
| Acknowledge ≥2 limitations / threats | **Six** documented. *(README §"Known limitations")* | e.g. (1) it measures *rhetorical* say–do consistency, not real behaviour; (2) sparse Part 1 years are carried forward → Apple & Berkshire stay unscored. |

### Part 4 — Proposal *(bonus — beyond the listed sub-tasks; [detail → `part4_proposal/README.md`](part4_proposal/README.md))*

| Brief requirement | How we did it (brief) | Real example (from `data/part4/`) |
|---|---|---|
| Propose + briefly implement an analysis you find genuinely interesting; report findings | Tests whether Part 3's rising alignment is genuine or **institutional herding**, via cross-firm profile dispersion over time. | Disclosed dispersion fell (**t = −6.3**) so the *raw* alignment rise is partly mechanical — but the *centered* (primary) measure survives the correction; twist: `sustainability_environment` cross-firm spread **grew +59%** — a *divergence* axis, not a bandwagon. |

## Design philosophy
Two principles run through everything, both straight from the brief: **document
every judgment call** (a well-justified imperfect choice beats an unjustified
one) and **build for scale** (50 is a sample; the code shouldn't know that).
Where the brief is deliberately ambiguous — value taxonomy, the meaning of
"alignment," Part 2 sourcing — the reasoning is written down at the point of
decision, in code comments and per-part READMEs.

## Status
**All four parts are complete** end-to-end on the full 50-company sample, each with
code + per-part README + output data + written summary: Part 1 from the Wayback Machine
(328/450 usable, LLM-themed), Part 2 from SEC EDGAR proxy statements (442/450
usable, 98%, classical metrics + LLM commitment layer), Part 3 the authenticity
index (375 company-years / 48 firms, peer-relative say↔do alignment, 3 validity
checks), and Part 4 the convergence/herding interrogation of that index
(cross-firm dispersion over time; the peer-relative measure survives the herding
correction, while sustainability emerges as a divergence axis).
