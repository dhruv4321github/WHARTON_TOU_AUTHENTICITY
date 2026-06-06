### Research Assistant Recruitment Assignment

Organizational Authenticity & Corporate Value Alignment

**Overview**

This assignment is a scoped proof of concept for a larger research project examining the alignment between what organizations *say* they value and what their behavior suggests they actually value. You will conduct the analysis on 50 of the 500 firms in the S&P 500, using a defined sample and a narrower time window — but the methods you develop should be explicitly designed to scale.

We are evaluating your technical skills, analytical judgment, and ability to handle incomplete instructions. Not everything below is fully specified. That is intentional.

**Companies to be evaluated (required for all parts)**

| # | Ticker | Company | Sector |
| --- | --- | --- | --- |
| 1 | MSFT | Microsoft | Technology |
| 2 | AAPL | Apple | Technology |
| 3 | NVDA | NVIDIA | Technology |
| 4 | GOOGL | Alphabet | Technology |
| 5 | META | Meta Platforms | Technology |
| 6 | AVGO | Broadcom | Technology |
| 7 | CRM | Salesforce | Technology |
| 8 | ORCL | Oracle | Technology |
| 9 | IBM | IBM | Technology |
| 10 | INTC | Intel | Technology |
| 11 | BRK.B | Berkshire Hathaway | Financials |
| 12 | JPM | JPMorgan Chase | Financials |
| 13 | BAC | Bank of America | Financials |
| 14 | WFC | Wells Fargo | Financials |
| 15 | GS | Goldman Sachs | Financials |
| 16 | MS | Morgan Stanley | Financials |
| 17 | BLK | BlackRock | Financials |
| 18 | SCHW | Charles Schwab | Financials |
| 19 | AXP | American Express | Financials |
| 20 | C | Citigroup | Financials |
| 21 | LLY | Eli Lilly | Healthcare |
| 22 | UNH | UnitedHealth Group | Healthcare |
| 23 | JNJ | Johnson & Johnson | Healthcare |
| 24 | ABBV | AbbVie | Healthcare |
| 25 | MRK | Merck | Healthcare |
| 26 | TMO | Thermo Fisher Scientific | Healthcare |
| 27 | ABT | Abbott Laboratories | Healthcare |
| 28 | PFE | Pfizer | Healthcare |
| 29 | MDT | Medtronic | Healthcare |
| 30 | BMY | Bristol-Myers Squibb | Healthcare |
| 31 | AMZN | Amazon | Consumer Discretionary |
| 32 | TSLA | Tesla | Consumer Discretionary |
| 33 | HD | Home Depot | Consumer Discretionary |
| 34 | MCD | McDonald's | Consumer Discretionary |
| 35 | NKE | Nike | Consumer Discretionary |
| 36 | SBUX | Starbucks | Consumer Discretionary |
| 37 | TGT | Target | Consumer Discretionary |
| 38 | LOW | Lowe's | Consumer Discretionary |
| 39 | TJX | TJX Companies | Consumer Discretionary |
| 40 | F | Ford Motor | Consumer Discretionary |
| 41 | XOM | ExxonMobil | Energy |
| 42 | CVX | Chevron | Energy |
| 43 | COP | ConocoPhillips | Energy |
| 44 | EOG | EOG Resources | Energy |
| 45 | SLB | SLB (Schlumberger) | Energy |
| 46 | MPC | Marathon Petroleum | Energy |
| 47 | PSX | Phillips 66 | Energy |
| 48 | VLO | Valero Energy | Energy |
| 49 | OXY | Occidental Petroleum | Energy |
| 50 | HAL | Halliburton | Energy |

**Deliverables (required for all parts)**

Every part must be submitted with:

- All code, fully commented, in a structured repository (GitHub preferred)

- A README.md per part documenting: what you did, why, what assumptions you made, what you would do differently with more time, and known limitations

- Output data files

- A written summary (max 1–2 pages per part), translating technical findings into substantive insights that a non-technical reader could act on

**Part 1 — Stated Values: Scraping "About Us" Pages via the Wayback Machine**

Using the Wayback Machine CDX API, collect archived snapshots of the corporate "About Us" (or equivalent mission/values) page for a sample of **50 companies**: the 10 largest by market cap in each of the following five GICS sectors — Technology, Financials, Healthcare, Consumer Discretionary, and Energy. Use the S&P 500 composition as of January 2024.

Collect **one snapshot per year** from 2016 through 2024 (9 time points per company; ~450 snapshots total).

- Define and document your criteria for identifying the correct page per company, and your rule for handling missing snapshots or redirect chains

- Extract visible body text, stripping navigation, footer, and boilerplate

- Using an LLM-based pipeline of your choice, analyze each snapshot for: (a) whether the page changed from the prior year, (b) what value/thematic categories are present (you define the categories — justify them), and (c) any notable linguistic shifts over time

- Produce a structured dataset: one row per company-year, with at minimum [ticker, company_name, sector, year, page_text_clean, changed_from_prior, theme_categories, analyst_notes]

*What we will look at:* the completeness of your scrape, the robustness of your text extraction, and the thoughtfulness of your analytical categories. We are not expecting 100% coverage — we are expecting you to document and justify every gap.

**Part 2 — Lived Values: ESG or Diversity Disclosure Analysis**

Select **one document type** — ESG report, sustainability report, DEI report, or proxy statement — and collect it for your same 50 companies across as many years as feasibly available in the 2016–2024 window.

You decide how to source these documents (company IR pages, SEC EDGAR, third-party aggregators, etc.). Document your source and any coverage gaps.

Apply text mining to analyze:

- Changes in language, tone, and topic emphasis over time within companies

- Cross-company and cross-sector variation

- Any shifts that appear to coincide with external events you identify as relevant

You may use any combination of classical NLP and LLM-assisted methods. Justify your choices.

Produce a structured dataset with a schema of your own design — but document every column and your reasoning for including it.

**Part 3 — Measure Construction: Organizational Authenticity Index**

Using your outputs from Parts 1 and 2, propose and implement a measure of organizational authenticity — the degree of alignment between what a company says it values and what its disclosures and behaviors suggest it actually prioritizes.

- Operationalize "alignment" explicitly: this is a theoretical and methodological choice, and we want to see your reasoning

- The measure should vary across companies and over time

- Report basic distributional properties and at least one validity check (e.g., does the measure behave in ways that make intuitive sense for companies you would expect to score high or low?).

- Acknowledge at least two limitations or threats to validity

There is no single correct answer here. We are evaluating the coherence and transparency of your reasoning as much as the measure itself.

**Part 4 — Your Proposal**

Propose one additional analysis you would run on your measure or the underlying data—something you find genuinely interesting. Briefly implement it (even a preliminary version) and report what you find.

Evaluation here weighs intellectual curiosity and scientific reasoning. A well-argued exploratory finding is worth more than a superficial confirmatory one.

**A note on ambiguity**

Several decisions in this assignment are deliberately left to you — including how to categorize values language, how to define "alignment," and how to source the Part 2 documents. We want to see how you navigate those choices. Document your reasoning clearly. A well-justified imperfect choice is always preferable to an unjustified one.
