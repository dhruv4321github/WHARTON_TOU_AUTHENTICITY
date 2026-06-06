# Part 2 — Lived Values: Disclosure Analysis (Proxy Statements via SEC EDGAR)

Sources one document type for the 50-company sample across 2016–2024, extracts its
text, and mines each document into a structured, cross-company-comparable row whose
topic-emphasis vector uses the *same* 10-category value taxonomy as Part 1 — so
Part 3 can compare "what they say" to "what they emphasize doing" on a common footing.

**Chosen document type: definitive proxy statements (SEC form DEF 14A), via EDGAR.**
We first explored voluntary ESG/sustainability report PDFs, but those proved
brittle to source at scale (patchy, no clean API), so we chose proxies — mandatory
annual filings with near-complete coverage behind an official, scalable API. Full
rationale and trade-offs below.

## Pipeline

```
config/companies.py
        │
        ▼
edgar.py          # resolve one DEF 14A per company-year + download (cached)
extract_filing.py # filing HTML/txt → clean body text
lexicons.py       # 10 category seed lexicons (= Part 1 taxonomy) + LM tone loader
mine.py           # classical metrics (+ optional LLM layer) → structured dataset
        │
        ▼
data/part2/part2_lived_values.csv   (one row per company-year)
data/part2/part2_coverage_report.csv
```

## Run it

```bash
pip install -r requirements.txt
# Default: SEC proxy statements via EDGAR (classical metrics, no API cost).
# SEC etiquette REQUIRES a descriptive User-Agent with a real contact email.
PYTHONPATH=. python -m part2_lived_values.mine --out-dir data/part2 \
    --user-agent "Your Name research (you@example.com)"
# Add the real Loughran-McDonald tone dictionary and/or the optional LLM layer:
PYTHONPATH=. python -m part2_lived_values.mine \
    --lm-dict path/to/LoughranMcDonald_MasterDictionary.csv --use-llm
```

---

## Document-type choice: proxy statements (DEF 14A) via EDGAR
The brief allows one of {ESG report, sustainability report, DEI report, proxy
statement}. We chose **proxy statements**, for two decisive reasons:

- **Coverage & sourcing reliability.** ESG/sustainability/DEI reports are
  *voluntary* PDFs on IR pages or aggregators — no clean, scalable API and uneven
  history, so coverage is patchy and hard to source reliably across 50+ firms.
  Proxies are *mandatory annual* SEC filings: EDGAR carries them for essentially
  every firm, every year (near-complete 2016–2024 coverage in our sample — e.g.
  **Thermo Fisher 9/9 on EDGAR vs 2/9 on the open web**), behind an official,
  documented, rate-limit-friendly API that scales to the full S&P 500.
- **Substantive fit.** Proxies disclose governance, executive pay, board
  composition/diversity, and (increasingly) human-capital and ESG oversight —
  concrete signals of what a firm *prioritizes and rewards*. They map onto the
  shared taxonomy (notably integrity/ethics→governance, people, diversity,
  financial/shareholder), keeping the Part 3 alignment measure coherent.

**Trade-off we accept:** proxies are more standardized and governance-weighted
than a discursive sustainability report, so they under-represent environmental
language relative to a CSR PDF. We judge reliable, complete, comparable coverage
across all 50 firms × 9 years to outweigh richer-but-spotty ESG PDFs.

## Sourcing strategy — SEC EDGAR (`edgar.py`)
Map ticker→CIK via EDGAR's official `company_tickers.json` (tolerating class-share
tickers, BRK.B→BRK-B, and a small `CIK_OVERRIDES` map for firms whose ticker now
points at a post-reorganization CIK — e.g. BlackRock's 2024 holding-co reorg —
whose pre-reorg history lives under a predecessor CIK). Pull the firm's full filing
history from the submissions API — **reading the older shard files, not just the
recent ~1000 filings, so 2016 proxies aren't missed** — keep `DEF 14A` filings, and
select one per calendar year (the newest, i.e. the annual-meeting proxy). The
primary document (HTML) is downloaded and cached by `(ticker, year)`. EDGAR
etiquette: descriptive User-Agent with contact info + ≤10 requests/sec.

**Year-duplicate guard.** Defensively, `mine.py` hashes each downloaded filing and,
if a later year's document is byte-identical to one already used, records that year
as `coverage_status = duplicate_of_prior` (with `duplicate_of_year` pointing at the
original) instead of feeding stale content into the time series — an honest gap,
not a fabricated datapoint.

## Coverage and documented gaps
**442 of 450 company-years (98%)** carry a usable proxy. The 8 gaps are recorded in
`part2_coverage_report.csv` and are mostly *structural*, not scrape failures:

- **Broadcom (AVGO), 2016–2018 — genuine and structural (the main reason it's not
  100%).** Before 2018, Broadcom was "Broadcom Limited," a **Singapore-domiciled
  foreign private issuer**. Foreign private issuers are **exempt from the SEC's
  proxy rules** (Securities Exchange Act §14(a)), so they file *no* DEF 14A. Broadcom
  became subject to U.S. proxy rules only after **redomiciling to the United States
  in 2018**, and its first proxy appears in 2019. So those three years have no proxy
  to find — the document legitimately does not exist, rather than us missing it.
- **Single-year edge cases:** AAPL 2018, MCD 2022, SBUX 2024, XOM 2021 (no DEF 14A
  matched in that calendar year — usually an annual-meeting/filing-date boundary
  effect), and NVDA 2022 (the filing's *primary document* was a short cover/wrapper
  that fell below the text threshold → flagged `scanned_or_empty`, not silently kept).
- **BlackRock (BLK) — an edge case we resolved, so NOT a gap.** Its ticker now maps
  to a CIK created in BlackRock's **2024 holding-company reorganization**, which
  holds only 2025+ filings; the 2016–2024 proxies live under the predecessor entity.
  We pin that predecessor CIK in `edgar.CIK_OVERRIDES`, recovering all 9 years. (This
  reorg-predecessor pattern is the one to watch when scaling to the full S&P 500.)

## Methods (and why)
**Classical layer (primary).** Cheap, reproducible, fully scalable, and—crucially—
transparent, which matters for a measure that feeds an authenticity index:
- *Topic emphasis*: hit counts for 10 category seed lexicons (`lexicons.py`),
  normalized into a share vector summing to 1. Stem-prefix matching
  (`innovat` → innovation/innovative). This 10-dim vector is the backbone of
  Part 3. Lexicons are hand-authored seeds meant to be expanded after inspecting
  real reports.
- *Tone*: Loughran-McDonald positive/negative/uncertainty/litigious word
  proportions + a net-tone score — the standard dictionary for corporate
  disclosure text. The full LM Master Dictionary is **not bundled** (large
  external file); pass it with `--lm-dict`. Without it a small, clearly-labelled
  fallback runs so the pipeline works, but real tone results require the genuine file.
- *Readability*: approximate Flesch Reading Ease (boilerplate/complexity proxy).
- *Within-company change*: cosine distance between consecutive years' emphasis
  vectors (0 = identical mix, 1 = orthogonal) + % change in length.

**LLM layer (optional, `--use-llm`).** On the filing's front matter (proxy
summary / letter), codes `concreteness` (vague aspiration ↔ quantified, time-bound
commitments) and `forward_orientation` (past achievements ↔ future targets) — an
authenticity-relevant rhetorical signal. Kept off the critical path and cached.

**Cross-sector & external-event analysis** (in the written summary, computed from
this dataset): emphasis vectors aggregated by sector and year reveal, e.g.,
whether Energy firms' `sustainability_environment` share rises around the 2015
Paris Agreement / 2021 net-zero wave, or whether `diversity_inclusion` share
jumps across sectors in 2020–2021. The dataset is built to support exactly these
groupby-year/sector comparisons.

## Output schema (`part2_lived_values.csv`) — every column + reasoning

| column | why it's here |
|---|---|
| `ticker`, `company_name`, `sector`, `year` | sample keys; sector enables cross-sector analysis |
| `report_url`, `report_source` | EDGAR filing URL + source (`edgar`) — provenance/auditability |
| `n_pages`, `n_words` | document scale (`n_pages` ≈ chars/3000 for HTML filings); length is itself an emphasis signal over time |
| `extract_status` | `ok` / `scanned_or_empty` / `extract_failed` — extraction QA |
| `emphasis_<category>` ×10 | the comparable topic-emphasis vector (core Part 3 input) |
| `top_category` | quick human-readable dominant theme |
| `lm_positive`, `lm_negative`, `lm_uncertainty`, `lm_litigious` | tone proportions |
| `net_tone` | (pos−neg)/(pos+neg); single tone summary |
| `flesch` | readability/complexity proxy |
| `emphasis_shift_cosine` | within-company year-over-year topic change (`None` first yr / after gap) |
| `word_count_delta_pct` | within-company change in report length |
| `llm_concreteness`, `llm_forward_orientation`, `llm_note` | optional commitment framing |
| `duplicate_of_year` | if this year's filing is byte-identical to an earlier year's, the year it duplicates (else blank) |
| `coverage_status` | `ok` / `not_found` / `download_failed` / `scanned_or_empty` / `extract_failed` / `duplicate_of_prior` |

## Known limitations
1. **Document-type bias.** Proxies are governance/compensation-weighted, so they
   *under-represent environmental language* vs. a sustainability report — a high
   `financial_growth_shareholder` / `integrity_ethics` share is partly the genre,
   not just the firm. Cross-firm/-year comparisons (same genre throughout) are
   sound; cross-*document-type* level comparisons against Part 1 must account for
   this (Part 3 compares *relative* profiles, not raw levels).
2. **Lexicon emphasis ≠ ground truth.** Seed lists are transparent but coarse;
   they measure *vocabulary share*, not sincerity. They should be expanded/validated.
3. **A filing is the firm's own account**, not independent behavior — so Part 2 is
   "lived values *as disclosed*," a caveat that matters for interpreting the Part 3
   measure (addressed there as a threat to validity).
4. **Tone uses the fallback dictionary unless `--lm-dict` is supplied** — net-tone
   numbers are indicative until the real Loughran-McDonald Master Dictionary is passed.
5. **Front-matter-only LLM coding** may miss commitments buried deep in long filings.

## Scaling
Nothing is hard-coded to 50; downloads/LLM calls are cached, and `--limit` /
`--only` support incremental runs. EDGAR is what makes ~500 companies × ~9 years
tractable: an official API, no IP-blocking, and a ticker→CIK map that covers the
whole index.
