# Part 1 — Stated Values: What 50 Large Firms *Say* They Value (2016–2024)

*A plain-English summary of the findings. Technical methods are in this folder's
README; this document is for a reader who just wants to know what we found and
whether to trust it.*

## What we did, in one paragraph
We used the Internet Archive's "Wayback Machine" to pull one archived copy per
year (2016–2024) of the "About Us" / mission / values page for 50 large U.S.
companies — the 10 biggest by market value in each of five industries
(Technology, Financials, Healthcare, Consumer Discretionary, Energy). We stripped
each page down to its real body text, automatically detected whether it had
changed from the prior year, and used a language model to score **how prominent
each of ten value themes** (innovation, customer focus, integrity, people,
diversity, sustainability, community, financial growth, quality, and global
reach) is on each page. The result is a year-by-year record of the *language* of
corporate self-presentation.

## How complete is the data (the honest version)
Of ~450 target company-years, **328 (73%) yielded usable values text.** Every one
of the 50 firms is represented in at least two years; none was silently dropped.
The gaps are real and documented, not papered over:
- Some pages simply weren't archived in a given year (the largest source of gaps).
- A few firms keep deliberately bare websites (Berkshire Hathaway) or are
  under-archived (Thermo Fisher effectively vanishes from the archive after 2017).
- Coverage by sector: Financials is strongest (80 of 90 firm-years), Healthcare
  and Energy the thinnest (58 and 60). These are documented in the coverage report.

**Bottom line on trust:** this is a robust sample of *how the language trends*,
not a perfect census. It is more than enough to compare sectors and track change
over time, which is what it's for.

## What we found

**1. Each industry has a distinct "values fingerprint."** The dominant theme on a
firm's values page is highly predictable from its industry:

| Industry | Most prominent stated value(s) |
|---|---|
| Technology | **Innovation** — overwhelmingly (far above any other theme) |
| Energy | **Sustainability/environment** — the *top* theme, ahead of even growth |
| Healthcare | A balance of **innovation, customers (patients), and people** |
| Financials | **Community & social impact**, then customers and employees |
| Consumer Discretionary | **Customers and community**, roughly tied |

The Energy result is the most striking: oil-and-gas and oilfield-services firms
now *lead* their public values language with environmental themes — more than
they emphasize financial growth.

**2. Sustainability language roughly doubled over the decade — and the jump is
recent.** Averaged across all 50 firms, the prominence of environmental themes
rose from ~0.16 (2016) to ~0.35 (2023), with a clear step-change around
**2020–2021** (the net-zero-pledge wave). The trend is sharpest in Energy, where
it went from ~0.27 (2016) to ~0.63 (2023) — environmental language more than
doubled on oil companies' own About pages.

**3. Diversity language rose modestly, peaked around 2022, then *receded*.**
Diversity/inclusion prominence drifted up to ~0.15 by 2022, then fell to ~0.08 by
2024 — a visible cooling in 2023–24. This is consistent with the broader public
retreat from DEI messaging, though it may also reflect such language migrating off
the main values page; we flag it as suggestive, not conclusive.

**4. These pages are living documents.** 61% of year-over-year comparisons showed
a substantive text change — companies actively rewrite how they describe
themselves, rather than setting it once. The language model's notes capture the
texture: e.g., for **ExxonMobil 2024** it flagged *"a notable increase in emphasis
on financial results and shareholder value"*; AbbVie's pages over time added
emphasis on R&D, ethics, and (around 2022) diversity and headcount.

## Why this matters / what to do with it
The headline for a non-technical reader: **what large firms say they value tracks
the prevailing social conversation** — environmental language surged after 2020,
diversity language has cooled since 2022 — and it varies sharply by industry.
That is exactly the "stated values" baseline this project needs: in Parts 2–3 we
compare this *talk* against what companies' ESG disclosures suggest they actually
*do*, to flag where the two diverge.

**Caveats to keep in mind.** (1) This measures *words on one page*, not sincerity
or behavior — a high sustainability score means the topic is prominent, not that
the firm is green. (2) The theme scores come from an automated language model;
they're consistent and reproducible but are a *measurement*, to be validated, not
ground truth. (3) Coverage gaps mean a few firms (e.g., Thermo Fisher) contribute
little to the time trend. All three are addressed head-on in the methods README.
