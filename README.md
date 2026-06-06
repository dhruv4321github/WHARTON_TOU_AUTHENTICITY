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
  mine.py                   #   classical metrics (+ optional LLM) → structured dataset
  README.md
common/
  llm.py                    # shared, provider-swappable LLM client (OpenAI)
part3_authenticity_index/   # [next] say-vs-do alignment measure
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
  emphasis vector shares Part 1's taxonomy; `SUMMARY.md` written. (Chosen over
  voluntary ESG/sustainability reports for coverage and sourcing reliability.)
- **Part 3 — Authenticity index.** An explicit, transparent operationalization
  of *alignment* between Part 1 and Part 2, varying across firms and over time,
  with distributional summary + a validity check.
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
Parts 1 and 2 collected end-to-end on the full 50-company sample: Part 1 from the
Wayback Machine (328/450 usable, LLM-themed, summary written), Part 2 from SEC
EDGAR proxy statements (442/450 usable, 98%). Remaining: Part 2 written summary,
Part 3 (authenticity index), Part 4 (proposal).
