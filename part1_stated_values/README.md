# Part 1 — Stated Values: Scraping "About Us" Pages via the Wayback Machine

This part collects, cleans, and structures the public "stated values" text for
the 50-company sample across 2016–2024 (one snapshot per company per year). The
interpretive layer (theme tagging, linguistic-shift notes) is a separate LLM
pass documented at the bottom; everything here is the deterministic, auditable
foundation it runs on.

## What it does (pipeline)

```
config/companies.py           # the sample + candidate value-page URLs
        │
        ▼
cdx.query_cdx()               # discover archived captures per candidate URL
cdx.coverage_score()          # rank candidates by years-covered → pick best page
cdx.select_one_per_year()     # one capture per year, nearest to a fixed anchor
        │
        ▼
extract.fetch_html()          # fetch RAW capture bytes (no Wayback chrome)
extract.extract_clean_text()  # strip nav/footer/boilerplate → body text
extract.text_changed()        # deterministic year-over-year change detection
        │
        ▼
data/part1/part1_stated_values.csv   (one row per company-year)
data/part1/part1_coverage_report.csv (per-company coverage + listed gaps)
```

## Run it

```bash
pip install -r requirements.txt
# Smoke test on three companies first:
PYTHONPATH=. python -m part1_stated_values.collect --only MSFT META SLB --out-dir data/part1
# Full sample:
PYTHONPATH=. python -m part1_stated_values.collect --out-dir data/part1
```

Raw HTML is cached under `data/part1/_html_cache/` keyed by capture
timestamp+digest, so re-runs and the later LLM pass never re-hit the Wayback
Machine. Set `--sleep` higher if you start seeing 429s.

---

## Key decisions (the parts the brief left to us)

### 1. Which page counts as the company's "values" page?
There is no canonical "About Us" URL, so we made identification **a probe, not a
guess**. For each company `config/companies.py` stores its primary domain plus a
short ordered list of candidate paths (`/about`, `/who-we-are`, company-specific
ones like J&J's `/credo`), a shared default path set, and any historical alias
domains. `choose_best_url()` queries CDX for every candidate and keeps the one
covering the **most of the 9 target years**. Ties are broken by **the config's
own best-first ordering** (the candidate listed earlier in `companies.py` wins),
then by total capture count. This ordering tiebreak is deliberate: a dedicated
values path (e.g. `jpmorganchase.com/about`) is listed ahead of the bare domain,
so on a tie we pick it rather than the busier-but-generic homepage — while firms
whose values page genuinely *is* a bare subdomain root (Amazon `aboutamazon.com`,
Meta `about.meta.com`) list `""` first and are therefore preserved. Rationale: a
wrong seed degrades gracefully into "second-best candidate" rather than silently
dropping a company, and the selection is reproducible from the recorded
`source_url`.

### 2. Which snapshot represents a year?
`select_one_per_year()` picks the capture **nearest to July 1** of each year.
Mid-year is an arbitrary-but-fixed anchor: it avoids Jan-1/Dec-31 snapshots that
straddle a redesign, and being fixed keeps selection unbiased across companies.
The anchor is a parameter (`--target` logic in `select_one_per_year`), so the
choice is visible and tunable, not baked in.

### 3. Missing snapshots and redirect chains
- **No capture in a target year** → row emitted with `coverage_status =
  no_snapshot_in_year` and empty text. An explicit, counted gap, never a silent
  omission. Change-detection does **not** bridge a gap (we only compare two
  consecutive *present* years).
- **No archived page for any candidate** → all 9 rows emitted as
  `no_page_found`. The company stays in the dataset as a visible coverage hole.
- **Redirects** → handled at two layers. CDX filtering keeps `statuscode:200`
  rows so the index points at real content; the fetcher follows any remaining
  capture-time redirect chain (`allow_redirects=True`).

### 4. Text extraction
Primary engine is **trafilatura** (`favor_recall=True`), purpose-built for
boilerplate removal and resilient to decade-old markup; a **BeautifulSoup**
fallback strips `script/style/nav/footer/header/aside/form` and takes the
remaining visible text when trafilatura returns too little. We fetch the
`…id_/…` raw-capture URL specifically so the Wayback toolbar/link-rewriting
doesn't contaminate the body text. Pages yielding <80 chars are flagged
`thin_text` rather than treated as real content.

### 5. Change detection — deliberately *not* the LLM's job
"Did the page change?" is deterministic and cheap, so we answer it with
normalized-text hashing + a `difflib` similarity ratio (`changed` when
similarity < 0.95). The 0.95 threshold tolerates trivial drift (copyright year,
a reworded button) while catching real revisions. We reserve the LLM strictly
for the interpretive questions, which also makes that pass cheaper.

---

## Output schema (`part1_stated_values.csv`)

| column | meaning |
|---|---|
| `ticker`, `company_name`, `sector`, `year` | sample keys |
| `snapshot_timestamp` | 14-digit Wayback capture time of the chosen snapshot |
| `snapshot_url` | raw-capture URL used (reproducible) |
| `source_url` | the value page chosen by the probe for this company |
| `http_status` | capture-time HTTP status |
| `page_text_clean` | extracted body text |
| `text_char_len` | length of cleaned text (quick quality signal) |
| `text_sha1` | hash of normalized text (dedup / exact-match) |
| `similarity_to_prior` | 0–1 ratio vs. prior present year (`None` if first/after gap) |
| `changed_from_prior` | bool / `None` |
| `coverage_status` | `ok` \| `thin_text` \| `no_snapshot_in_year` \| `no_page_found` |
| `theme_categories` | **filled by the LLM pass** (value taxonomy) |
| `analyst_notes` | **filled by the LLM pass** (notable linguistic shifts) |

This satisfies the brief's required minimum
`[ticker, company_name, sector, year, page_text_clean, changed_from_prior,
theme_categories, analyst_notes]` and adds provenance/QA columns.

## Coverage and documented gaps
**328 of 450 company-years (73%)** yield usable values text. Every one of the 50
firms is represented in **at least two years** — none is silently dropped — and
after the seed-path fixes there are **zero `no_page_found` companies**. Per-company
`gap_years` are enumerated in `part1_coverage_report.csv`.

Unlike Part 2 (8 gaps, each individually explicable), Part 1's gaps are dominated
by the *inherent stochasticity of opportunistic web archival* — the Wayback Machine
crawls a page when it happens to, not on a schedule. So we justify gaps **by
category** (the `coverage_status` taxonomy) plus per-company enumeration and
structural notes, rather than a unique reason for each of 122 "not-crawled-that-year"
rows (which wouldn't be meaningful):

- **`no_snapshot_in_year` (111 rows) — the dominant, irreducible gap.** The chosen
  page simply wasn't captured in that calendar year. We emit an explicit empty row,
  never interpolate, and change-detection does not bridge a gap (only consecutive
  *present* years are compared).
- **`thin_text` (11 rows).** A snapshot exists but extracted <80 chars — typically a
  JS-only or deliberately bare page (**Berkshire Hathaway**'s famously minimal site).
  Flagged, not treated as real values content.
- **`no_page_found` (0).** After correcting seeds to match how pages are *archived*
  (`.html`/`.page` suffixes — see limitation #5), every firm resolves to a real page.

Structural standouts in the low-coverage tail (all in `part1_coverage_report.csv`):
- **Thermo Fisher (2/9) — a genuine hole.** Its site largely disappears from the
  Wayback Machine after 2017 (likely a robots.txt exclusion); not recoverable from
  the archive, so it stays a documented gap.
- **Apple, Broadcom, American Express, UnitedHealth, Target (2/9).** The chosen
  single page is only sparsely archived; a better-covered *alternate* page may exist
  for some (the "one page ≠ all stated values" scope limit, #2) — flagged for
  follow-up, not chased.
- **Meta (4/9) and SLB (4/9).** Mid-window **rebrands** (Facebook→Meta 2021;
  Schlumberger→SLB 2022) split coverage across domains — substantive value-language
  events, documented in the `companies.py` notes and probed via alias domains.

## Substantively interesting cases already flagged in the seed config
- **Meta** (Facebook → Meta, Oct 2021) and **SLB** (Schlumberger → SLB, 2022):
  domain rebrands that are *substantive value-language events*, not mere gaps.
  Aliases (`fb.com`, `schlumberger.com`) are probed so we keep the full arc.
- **Berkshire Hathaway**: famously bare site → expect `thin_text`; its real
  values text is Buffett's letters (PDFs), a natural bridge to Part 2.
- **Apple**: no classic About page; values surface via leadership/values pages.

## Known limitations
1. **Coverage is honest, not complete.** Some company-years will be gaps; the
   coverage report quantifies exactly how many and where. We optimize for
   documented gaps over fabricated completeness.
2. **One page ≠ all stated values.** A single value page understates firms that
   spread mission language across many pages. Defensible for comparability;
   noted as a scope choice.
3. **Mid-year anchor** can miss a value statement that was live only briefly.
4. **trafilatura is good, not perfect** on heavily JS-rendered captures (rare in
   the archive, which stores server HTML, but possible for late-window pages).
5. **Seed paths must match how the page is *archived*, not how it looks today.**
   CDX matches exact URL keys, so a bare-directory seed (`abbvie.com/about-us`)
   returns 0 captures when the archived page is `abbvie.com/our-company.html` —
   older corporate sites use `.html`/`.page` suffixes and nested paths. When a
   company comes back `no_page_found`, confirm with a CDX **prefix scan**
   (`url=domain/*`) before calling it a real gap; several Healthcare/Energy seeds
   were corrected this way (see the per-company `notes` in `config/companies.py`).
   A genuinely under-archived site (Thermo Fisher: gone from Wayback after 2017)
   stays a documented hole.

## How this scales (the brief's real ask)
Nothing is hard-coded to 50. Replace the seed list with the full S&P 500, raise
`--limit`, and the same code runs ~4,500 snapshots. The HTML cache + polite
retry/backoff are what make that feasible; the probe-don't-guess URL strategy is
what makes it survive without per-company hand-tuning. Two operational knobs from
real runs: `--cdx-timeout` (web.archive.org's CDX endpoint can take 40–50s/query
when throttled — a short timeout silently empties real pages), and
`part1_stated_values/merge.py`, which splices a `--only` re-collection of a few
tickers back into the full dataset (handy for re-running the apparent empties a
throttled bulk run produces, without re-running all 500).

## Analysis layer (`analyze.py`) — built
Fills `theme_categories` and `analyst_notes` via an LLM (OpenAI by default,
through a swappable `LLMClient`).

### The value taxonomy (the central judgment call) — and why these 10

The brief explicitly leaves the categories to us ("you define the categories —
justify them"). We use **10 sector-neutral value categories**. The full
definitions live in the `TAXONOMY` dict in `analyze.py`; here is the list and the
reasoning behind it.

| Category | What it captures |
|---|---|
| `innovation_technology` | R&D, invention, technological leadership, being cutting-edge/disruptive |
| `customer_focus` | Serving, delighting, or being obsessed with customers; service quality |
| `integrity_ethics` | Honesty, ethics, trust, transparency, accountability, governance |
| `people_talent` | Employees, talent, development, wellbeing, culture, being a great workplace |
| `diversity_inclusion` | Diversity, equity, inclusion, belonging, representation |
| `sustainability_environment` | Climate, emissions, energy transition, environmental stewardship, net-zero |
| `community_social_impact` | Communities, philanthropy, social responsibility, broadening access |
| `financial_growth_shareholder` | Growth, profitability, shareholder value, returns, scale as a goal |
| `quality_excellence` | Quality, operational excellence, reliability, craftsmanship, safety |
| `global_scale_reach` | Global presence/reach; serving the world; the scale of operations |

Three design principles drove the choice:

1. **Sector-neutral, so cross-sector comparison is meaningful.** The same 10
   buckets must fit a bank, an oil major, and a hospital — otherwise the brief's
   five-sector comparison is impossible. We deliberately avoided industry-specific
   labels (no "drug pipeline," no "loan growth"); every category is phrased so any
   of the 50 firms could plausibly express it.
2. **They bridge to Part 2 — this is the load-bearing reason.** The categories are
   chosen to map onto the **ESG + business-performance** dimensions that Part 2
   measures in the proxy statements, so Part 3 can compute say-vs-do *alignment* on
   a single common footing instead of comparing two incommensurable vocabularies.
   The taxonomy is, in effect, the shared language that makes Part 3 possible — it
   was reverse-engineered from what the alignment measure needs. The explicit
   mapping (also in `analyze.py`):
   - **Environmental** → `sustainability_environment`
   - **Social** → `people_talent`, `diversity_inclusion`, `community_social_impact`,
     `customer_focus`
   - **Governance** → `integrity_ethics`
   - **Business/Performance** → `innovation_technology`,
     `financial_growth_shareholder`, `quality_excellence`, `global_scale_reach`
3. **Multi-label, not one forced label.** A real values page is usually about
   several things at once (Nike: innovation *and* community *and* sustainability),
   so each category gets a **0–1 salience score** and a page can light up several.
   This reflects how mission text actually reads and gives Part 3 a 10-number
   *profile* per company-year rather than a single crude tag.

**Why 10** is a deliberate middle ground: few enough to stay interpretable and to
score reliably, many enough to keep genuinely distinct values apart (firms
emphasize `people_talent` and `diversity_inclusion` very differently, so they must
not be merged). The scheme is **versioned** (`TAXONOMY_VERSION`) and that version
is part of the LLM cache key, so changing the categories invalidates every stale
coding rather than silently mixing schemes.

**Honest limitation of the taxonomy.** It is a *defensible* lens, not the only
one. Being sector-neutral is a strength for comparison but a mild cost in nuance
(it can't separate, say, "patient safety" from generic `quality_excellence`). And
the top-down, ESG-aligned framing is itself a choice: one could instead build the
categories *inductively* (let topics emerge from the text). We chose the top-down,
Part-2-bridged scheme precisely because Parts 2–3 need a fixed shared space — a
stated trade-off, not a free lunch.

### Scoring and cost discipline
- **Theme scoring** is multi-label with 0–1 salience per category, not a single
  forced label. The model's output is filtered to the fixed 10 keys with scores
  clamped to 0–1 (`_clean_themes`), so it cannot invent a category or an
  out-of-range score.
- **Cost discipline:** the model is only called for `ok` rows; identical-text
  years reuse the prior coding with no call; shift notes are only generated when
  the deterministic detector flagged a change; all calls are cached on disk.

Run: `export OPENAI_API_KEY=...` then
`PYTHONPATH=. python -m part1_stated_values.analyze`
(model defaults to `$OPENAI_MODEL` or `gpt-4o-mini`; override with `--model`).
