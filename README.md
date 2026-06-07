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
part4_proposal/             # [next] an exploratory analysis of our own
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
- **Part 4 — Proposal.** One genuinely interesting follow-on analysis, implemented
  at least preliminarily.

## Design philosophy
Two principles run through everything, both straight from the brief: **document
every judgment call** (a well-justified imperfect choice beats an unjustified
one) and **build for scale** (50 is a sample; the code shouldn't know that).
Where the brief is deliberately ambiguous — value taxonomy, the meaning of
"alignment," Part 2 sourcing — the reasoning is written down at the point of
decision, in code comments and per-part READMEs.

## Status
Parts 1–3 are complete end-to-end on the full 50-company sample, each with code +
per-part README + output data + written summary: Part 1 from the Wayback Machine
(328/450 usable, LLM-themed), Part 2 from SEC EDGAR proxy statements (442/450
usable, 98%, classical metrics + LLM commitment layer), Part 3 the authenticity
index (375 company-years / 48 firms, peer-relative say↔do alignment, 3 validity
checks). Remaining: Part 4 (proposal).
