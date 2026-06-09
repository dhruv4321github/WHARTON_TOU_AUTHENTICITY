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
mine.py           # classical metrics (+ LLM layer) → structured dataset
        │
        ▼
data/part2/part2_lived_values.csv   (one row per company-year)
data/part2/part2_coverage_report.csv
        │
        ▼
analysis.py       # reproducible over-time / cross-sector / external-event tables
        │
        ▼
data/part2/analysis_within_company.csv      analysis_sector_fingerprint.csv
data/part2/analysis_sector_year.csv         analysis_events.csv
```

## Run it

```bash
pip install -r requirements.txt
# Default: SEC proxy statements via EDGAR (classical metrics, no API cost).
# SEC etiquette REQUIRES a descriptive User-Agent with a real contact email.
PYTHONPATH=. python -m part2_lived_values.mine --out-dir data/part2 \
    --user-agent "Your Name research (you@example.com)"
# Add the real Loughran-McDonald tone dictionary and/or the LLM layer:
PYTHONPATH=. python -m part2_lived_values.mine \
    --lm-dict path/to/LoughranMcDonald_MasterDictionary.csv --use-llm
# Then regenerate the over-time / cross-sector / external-event analysis tables
# (pure pandas, no network/API cost; --plots also writes two PNG trend charts):
PYTHONPATH=. python -m part2_lived_values.analysis --plots
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

**LLM layer (`--use-llm`) — run for the full sample.** On the filing's front
matter (notice / board-chair or CEO letter / proxy summary, first ~8k chars), it
codes `concreteness` (vague aspiration ↔ quantified, time-bound commitments) and
`forward_orientation` (past achievements ↔ future targets) — an
authenticity-relevant rhetorical signal that gives Part 3 a *second* dimension
(rhetorical substance) on top of topic alignment. The prompt is adapted to proxy
front matter (not a generic ESG letter). We ran it across all **442/442 usable
filings (0 errors)**; results sit in the `llm_*` columns and every call is cached
on disk, so it stays off the classical critical path and re-runs are free.
Distributions are sane: `concreteness` mean ≈ 0.69, `forward_orientation` mean
≈ 0.75 — proxies are moderately concrete and strongly forward-looking, exactly as
the genre predicts.

**The three analyses the brief asks for are *computed*, not just narrated** — see
the Analysis layer below.

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

## Analysis layer (`analysis.py`) — the brief's three required analyses, reproducibly
The brief asks us to *apply text mining to analyze* (1) over-time change within
firms, (2) cross-company/-sector variation, and (3) shifts coinciding with external
events. `mine.py` bakes the within-firm year-over-year signal into the dataset
(`emphasis_shift_cosine`, `word_count_delta_pct`); `analysis.py` regenerates the
rest from the committed CSV in one command — so every number in `SUMMARY.md` is
auditable, not hand-computed. It is pure pandas/numpy (no network, no API cost, no
scipy); `--plots` additionally writes two trend charts
(`fig_sustainability_by_sector.png`, `fig_diversity_over_time.png`; y-axes
baselined at 0 so a near-flat series isn't visually exaggerated).

| output | what it answers |
|---|---|
| `analysis_within_company.csv` | (1) per firm: mean YoY topic churn, **net start→end drift** (cosine), tone/readability trend, and the single biggest rising/falling theme. Sorted by drift, so the biggest movers (e.g. Valero, Tesla, BlackRock) surface first. |
| `analysis_sector_fingerprint.csv` | (2) each sector's mean 10-theme emphasis + tone + LLM framing — its "fingerprint" (e.g. Tech proxies top out on `diversity_inclusion` ~0.22; Financials are the only net-negative-tone sector). |
| `analysis_sector_year.csv` | (2)+(3) full sector × year emphasis trend table (backbone for the event windows). |
| `analysis_events.csv` | (3) for each event, a **paired pre→post test** across firms present in both windows. |

**External-event method (transparent, not a fishing trip).** Each event is a
*pre-registered hypothesis* — it names the theme it should move and the window it
should move in (`EVENTS` in `analysis.py`, with rationale at the point of decision).
Windows are on filing year with a one-year buffer around the event (proxies are
filed early, for the prior year). For firms present in **both** windows we report a
paired pre/post comparison: levels, % change, a hand-computed paired **t-stat**
(no scipy), and a nonparametric **`frac_increased`** (share of firms moving up) so a
shift can be judged without overclaiming significance on ~50 firms.

What it finds, bluntly: **only the climate/net-zero window is robust** —
`sustainability_environment` ~doubles (all firms 0.041→0.098, **98% of firms up,
t≈8.8**; Energy 0.081→0.190, **100% up, t≈5.6**). The 2020 **DEI/human-capital**
and **COVID** windows are *not* sustained level shifts (≈+2%, t<1, ~half of firms
up) — diversity language shows only a small, transient 2021 peak, not a durable
re-leveling. Reporting the null results alongside the strong one is the honest
scientific outcome.

## Known limitations
1. **Document-type bias — the proxy has its own built-in "accent."** A proxy
   statement's legal job is governance, board elections, and executive pay, so
   *every* firm's proxy automatically sounds money- and ethics/governance-heavy and
   light on the environment — that tilt comes from the *document type*, not from the
   specific company. (Had we picked a sustainability report, the tilt would flip the
   other way.) So when a firm's proxy scores high on
   `financial_growth_shareholder` / `integrity_ethics`, part of that is just "this is
   a proxy," not "this firm uniquely prioritizes money and ethics." **What this does
   and doesn't break:** comparing one firm's proxy to another's, or one year to the
   next, is *fair* — every document is the same genre, so the bias is the same
   constant for all and cancels out. What's *not* fair is directly comparing the
   proxy's **raw** topic levels against Part 1's website pages, which are a different
   genre that discusses the environment far more freely — the proxy will always look
   lower on environment regardless of what the firm truly cares about. This is
   exactly why **Part 3 compares each firm *relative to its peers* on the same side**
   (which subtracts out the shared genre tilt) rather than comparing raw numbers.
2. **Lexicon emphasis ≠ ground truth.** Seed lists are transparent but coarse;
   they measure *vocabulary share*, not sincerity, and should be expanded/validated
   against real reports. (Why lexicon-counting here, instead of LLM topic-scoring as
   in Part 1? Proxy statements run to tens of thousands of words — *far* longer than
   Part 1's short "About Us" pages — so an LLM pass over every full filing would be
   slow and costly, whereas word-counting is cheap, transparent, and scales to all
   500 firms.)
3. **A filing is the firm's own account**, not independent behavior — so Part 2 is
   "lived values *as disclosed*," a caveat that matters for interpreting the Part 3
   measure (addressed there as a threat to validity).
4. **Tone uses the fallback dictionary unless `--lm-dict` is supplied** — so the
   *shipped* net-tone numbers are **indicative, not final** (the committed run used
   the small built-in fallback list). We didn't bundle the real Loughran-McDonald
   Master Dictionary because it's a large external file, so tone is an
   **optional, one-flag** layer: a natural next step is to download the genuine
   dictionary, re-run with `--lm-dict path/to/LM.csv`, and regenerate real tone
   numbers. This affects only the tone columns — the topic-emphasis vectors that feed
   Part 3 don't depend on it.
5. **Front-matter-only LLM coding** may miss commitments buried deep in long filings.

## Scaling
Nothing is hard-coded to 50; downloads/LLM calls are cached, and `--limit` /
`--only` support incremental runs. EDGAR is what makes ~500 companies × ~9 years
tractable: an official API, no IP-blocking, and a ticker→CIK map that covers the
whole index.
