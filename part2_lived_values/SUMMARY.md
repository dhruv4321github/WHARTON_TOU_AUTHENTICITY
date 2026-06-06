# Part 2 — Lived Values: What 50 Large Firms *Disclose* (Proxy Statements, 2016–2024)

*Plain-English summary. Methods and the full column schema are in this folder's
README; this is for a reader who wants the findings and whether to trust them.*

## What we did, in one paragraph
For the same 50 firms as Part 1, we collected each company's **annual proxy
statement** (SEC form DEF 14A) for 2016–2024 from the SEC's EDGAR database,
extracted the text, and scored **how prominent each of the same ten value themes**
is in each filing (the identical taxonomy used in Part 1, so the two are directly
comparable). A proxy statement is the document a public company must file before
its annual shareholder meeting; it discloses the board, executive pay, governance,
board diversity, and — increasingly — human-capital and ESG oversight. It is a good
window onto **"lived values"** because it reports what a firm actually *structures,
governs, and pays for*, not what it chooses to put in a marketing brochure.

## Why proxy statements (a deliberate pivot)
The brief allowed any one of: ESG report, sustainability report, DEI report, or
proxy statement. The first three are *voluntary* PDFs with patchy history and no
clean, scalable source, so coverage across 50 firms is unreliable. **Proxy
statements are mandatory annual SEC filings**, so we source them from EDGAR — an
official, scalable API. The payoff in coverage was decisive (below). The
trade-off, stated up front: proxies are governance- and
compensation-weighted, so they feature *less* environmental language than a
dedicated sustainability report would — a genre effect we account for in Part 3.

## How complete is the data
**442 of 450 company-years (98%)** — essentially the whole sample, every year.

- The 8 gaps are documented and mostly genuine: **Broadcom 2016–18** (it was a
  Singapore-domiciled "foreign private issuer," legally exempt from U.S. proxy
  rules — so no DEF 14A exists), plus a handful of single-year edge cases
  (Apple 2018, McDonald's 2022, NVIDIA 2022, Starbucks 2024, ExxonMobil 2021).
- Firms that were *coverage holes* in Part 1 are now complete here — e.g. Thermo
  Fisher went from 2/9 (vanished from the public web) to **9/9** on EDGAR.

This is the kind of near-census the "lived values" measure needs.

## What we found

**1. Proxies have a clear, shared "fingerprint" — and it differs from the website.**
Across all sectors the dominant themes are **financial/shareholder, governance &
ethics, people, and diversity** — exactly what proxies are *about* (pay, board,
oversight). Notably, **diversity language is far more prominent here than on
companies' About pages** (Technology proxies average the highest, ~0.22 share),
because proxies disclose board composition and diversity directly. This contrast
is the whole point of the project: Tech firms' websites lead with *innovation*
(Part 1), but their mandatory disclosures emphasize *governance, people, and
diversity*. Part 3 turns that say-vs-do gap into a number.

**2. Environmental language roughly doubled — concentrated in Energy.** Averaged
across all 50 firms, the sustainability/environment share of proxy language rose
from ~0.04 (2016) to ~0.10 (2022–2024), with a clear step-up in **2022**. The move
is sharpest in **Energy**, where it more than doubled (~0.09 in 2016 to a peak
~0.21 in 2022) — oil-and-gas firms putting climate/transition language into the
documents shareholders vote on, not just their websites.

**3. Diversity and human-capital language rose modestly and recently, then cooled.**
Both tick up to local peaks around **2021** (diversity ~0.18; people/human-capital
~0.18 — consistent with the 2020 racial-justice moment and the SEC's 2020
human-capital disclosure rule) and then ease back by 2023–24. The aggregate moves
are modest; they're sharper for individual firms.

**4. Tone separates the financial sector from everyone else.** Using a
finance-specific tone dictionary, **Financials are the only sector with net-negative
tone (~−0.20)** — banks' proxies are dense with risk, litigation, and compliance
language — while Healthcare (+0.39), Technology (+0.32), and Energy (+0.33) skew
positive. (Tone here uses a small fallback word list; the headline pattern is
robust, but precise tone values firm up with the full Loughran-McDonald dictionary.)

## Why this matters / what to do with it
The headline: **what firms are legally required to disclose looks different from
what they advertise.** Proxies foreground governance, pay, board diversity, and a
rising-but-still-small strand of climate language; the website (Part 1) foregrounds
innovation and customers. That divergence is not hypocrisy by itself — it's partly
the genre — but it is precisely the raw material for an **authenticity measure**:
where a firm's *stated* emphasis and its *disclosed* emphasis line up, and where
they don't. Part 3 builds that comparison on the shared 10-theme space.

**Caveats.** (1) **Genre bias** — proxies under-weight environmental language vs. a
sustainability report, so cross-document-type *levels* aren't directly comparable;
Part 3 compares *relative profiles*. (2) **A disclosure is the firm's own account**,
not independently verified behavior. (3) The theme scores are an automated,
reproducible *measurement* (dictionary-based), to be validated, not ground truth.
(4) Tone uses a fallback dictionary unless the full LM file is supplied. All four
are documented in the methods README.
