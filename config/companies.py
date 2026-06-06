"""
Seed configuration for the 50-company sample.

This is the single source of truth for *which* companies we analyze and *where*
their "stated values" pages live. It is required by all four parts of the
assignment, so it lives in a shared `config/` package rather than inside Part 1.

Sample definition (from the assignment):
    The 10 largest firms by market cap in each of five GICS sectors
    (Technology, Financials, Healthcare, Consumer Discretionary, Energy),
    using S&P 500 composition as of January 2024. The exact 50 tickers were
    given in the assignment brief and are reproduced verbatim below.

A note on the `domain` / `about_paths` fields
----------------------------------------------
There is no canonical, machine-readable list of "the About Us page" for a
company. Identifying the right page is itself one of the judgment calls the
assignment asks us to document. Our approach (see part1_stated_values/README.md):

  1. For each company we record its primary registrable domain in the
     2016-2024 window and a SHORT, ORDERED list of *candidate* mission/values
     paths, most-likely first.
  2. The collector probes every candidate against the Wayback CDX API and keeps
     the one with the best longitudinal coverage (most of the 9 target years
     archived). This is deterministic and reproducible, and it means a wrong
     guess below degrades gracefully rather than silently dropping a company.
  3. `aliases` records historical domains so we don't lose a company that
     rebranded mid-window (the two big ones are flagged in `notes`).

The seeds below are informed best-guesses, not assumed-correct. The probe is
what actually decides; these just keep the search space small and polite.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Company:
    rank: int                       # 1-10 within sector, by Jan-2024 market cap
    ticker: str
    name: str
    sector: str
    domain: str                     # primary registrable domain, 2016-2024
    about_paths: tuple[str, ...]    # candidate mission/values paths, best-guess first
    aliases: tuple[str, ...] = ()   # historical domains to also probe
    notes: str = ""                 # analyst-relevant caveats (rebrands, sparse sites)


# Paths probed for every company in addition to its company-specific guesses.
# Ordered roughly by how commonly large US firms use them.
DEFAULT_ABOUT_PATHS: tuple[str, ...] = (
    "about",
    "about-us",
    "company",
    "company/about-us",
    "our-company",
    "who-we-are",
    "mission",
    "values",
    "purpose",
)


COMPANIES: tuple[Company, ...] = (
    # ---- Technology -------------------------------------------------------
    Company(1, "MSFT", "Microsoft", "Technology", "microsoft.com",
            ("about", "en-us/about", "corporate-responsibility")),
    Company(2, "AAPL", "Apple", "Technology", "apple.com",
            ("about", "leadership", "values"),
            notes="Apple has no traditional 'About Us' page; values surface via "
                  "leadership / values / diversity pages. Probe decides."),
    Company(3, "NVDA", "NVIDIA", "Technology", "nvidia.com",
            ("about-nvidia", "en-us/about-nvidia", "about")),
    Company(4, "GOOGL", "Alphabet", "Technology", "about.google",
            ("", "intl/en/about", "our-commitments"),
            aliases=("abc.xyz", "google.com"),
            notes="Mission/values live on about.google; corporate parent is "
                  "abc.xyz (Alphabet). Probe both."),
    Company(5, "META", "Meta Platforms", "Technology", "about.meta.com",
            ("", "company-info", "company"),
            aliases=("about.fb.com", "newsroom.fb.com", "facebook.com"),
            notes="Renamed Facebook -> Meta in Oct 2021. Pre-2022 snapshots live "
                  "under fb.com domains. This rebrand is a substantive linguistic "
                  "event, not just a coverage gap."),
    Company(6, "AVGO", "Broadcom", "Technology", "broadcom.com",
            ("company", "company/about-us", "about")),
    Company(7, "CRM", "Salesforce", "Technology", "salesforce.com",
            ("company/about-us", "company", "company/our-story")),
    Company(8, "ORCL", "Oracle", "Technology", "oracle.com",
            ("corporate", "about", "corporate/citizenship")),
    Company(9, "IBM", "IBM", "Technology", "ibm.com",
            ("about", "ibm/about", "impact")),
    Company(10, "INTC", "Intel", "Technology", "intel.com",
            ("about", "content/www/us/en/company-overview/company-overview.html",
             "corporate-responsibility")),

    # ---- Financials -------------------------------------------------------
    Company(11, "BRK.B", "Berkshire Hathaway", "Financials", "berkshirehathaway.com",
            ("", "message.html"),
            notes="Famously minimal site (essentially a link page). Expect thin "
                  "extracted text; Buffett's annual letters are the real 'values' "
                  "text but live as PDFs. Document as a coverage edge case."),
    Company(12, "JPM", "JPMorgan Chase", "Financials", "jpmorganchase.com",
            ("about", "about/our-business", "")),
    Company(13, "BAC", "Bank of America", "Financials", "about.bankofamerica.com",
            ("", "en/our-company", "en/who-we-are"),
            aliases=("bankofamerica.com",)),
    Company(14, "WFC", "Wells Fargo", "Financials", "wellsfargo.com",
            ("about", "about/corporate", "about/our-culture")),
    Company(15, "GS", "Goldman Sachs", "Financials", "goldmansachs.com",
            ("our-firm", "about-us", "what-we-do")),
    Company(16, "MS", "Morgan Stanley", "Financials", "morganstanley.com",
            ("about-us", "about-us/our-firm", "what-we-do")),
    Company(17, "BLK", "BlackRock", "Financials", "blackrock.com",
            ("corporate/about-us", "corporate", "us/individual/about-us")),
    Company(18, "SCHW", "Charles Schwab", "Financials", "aboutschwab.com",
            ("", "about", "who-we-are"),
            aliases=("schwab.com",)),
    Company(19, "AXP", "American Express", "Financials", "americanexpress.com",
            ("about-us", "en-us/company", "company"),
            aliases=("about.americanexpress.com",)),
    Company(20, "C", "Citigroup", "Financials", "citigroup.com",
            ("about", "citi/about", "about/mission-and-value-proposition")),

    # ---- Healthcare -------------------------------------------------------
    Company(21, "LLY", "Eli Lilly", "Healthcare", "lilly.com",
            ("about", "who-we-are", "purpose")),
    Company(22, "UNH", "UnitedHealth Group", "Healthcare", "unitedhealthgroup.com",
            ("about", "who-we-are", "values.html")),
    Company(23, "JNJ", "Johnson & Johnson", "Healthcare", "jnj.com",
            ("about-jnj", "credo", "about-jnj/our-credo"),
            notes="J&J's 'Credo' is its canonical values statement; probe it "
                  "explicitly alongside about-jnj."),
    Company(24, "ABBV", "AbbVie", "Healthcare", "abbvie.com",
            ("our-company.html", "about-us", "who-we-are", "our-company"),
            notes="Archived pages use .html suffixes; bare /about-us has 0 captures. "
                  "our-company.html covers 2017-2023 (found via Wayback prefix scan)."),
    Company(25, "MRK", "Merck", "Healthcare", "merck.com",
            ("about", "company-overview", "our-company")),
    Company(26, "TMO", "Thermo Fisher Scientific", "Healthcare", "thermofisher.com",
            ("us/en/home.html", "us/en/home/about-us.html", "about-us"),
            notes="Thermo Fisher is largely absent from the Wayback Machine after 2017 "
                  "(heavily captured 2016-17, then almost nothing; likely a robots.txt "
                  "exclusion). Best-available us/en/home.html covers only 2016-2017 -> a "
                  "documented coverage hole, NOT a seed error."),
    Company(27, "ABT", "Abbott Laboratories", "Healthcare", "abbott.com",
            ("about-abbott/who-we-are.html", "about-abbott.html", "about-abbott"),
            notes="Archived pages use .html suffixes; who-we-are.html covers 2016-2024 (9/9)."),
    Company(28, "PFE", "Pfizer", "Healthcare", "pfizer.com",
            ("about", "purpose", "people")),
    Company(29, "MDT", "Medtronic", "Healthcare", "medtronic.com",
            ("about", "us-en/about.html", "us-en/about/mission.html")),
    Company(30, "BMY", "Bristol-Myers Squibb", "Healthcare", "bms.com",
            ("about-us/our-company.html", "about-us.html", "about-us"),
            notes="Archived pages use .html suffixes; about-us/our-company.html covers 2017-2024."),

    # ---- Consumer Discretionary ------------------------------------------
    Company(31, "AMZN", "Amazon", "Consumer Discretionary", "aboutamazon.com",
            ("", "about-us", "workplace/our-mission"),
            aliases=("amazon.com",)),
    Company(32, "TSLA", "Tesla", "Consumer Discretionary", "tesla.com",
            ("about", "car-overview", "ns_videos/about.html")),
    Company(33, "HD", "Home Depot", "Consumer Discretionary", "corporate.homedepot.com",
            ("about", "", "values"),
            aliases=("homedepot.com",)),
    Company(34, "MCD", "McDonald's", "Consumer Discretionary", "corporate.mcdonalds.com",
            ("us/en-us/about-us.html", "corpmcd/home.html", "", "corpmcd/our-company.html"),
            aliases=("mcdonalds.com", "aboutmcdonalds.com"),
            notes="corporate.mcdonalds.com about pages are sparsely archived; the "
                  "well-covered values page is mcdonalds.com/us/en-us/about-us.html "
                  "(9/9), reached via the mcdonalds.com alias."),
    Company(35, "NKE", "Nike", "Consumer Discretionary", "about.nike.com",
            ("", "company", "our-mission"),
            aliases=("nike.com",)),
    Company(36, "SBUX", "Starbucks", "Consumer Discretionary", "starbucks.com",
            ("about-us", "about-us/company-information", "about-us/our-mission-values"),
            aliases=("stories.starbucks.com",)),
    Company(37, "TGT", "Target", "Consumer Discretionary", "corporate.target.com",
            ("about", "", "about/purpose-values"),
            aliases=("target.com",)),
    Company(38, "LOW", "Lowe's", "Consumer Discretionary", "corporate.lowes.com",
            ("about", "", "our-company"),
            aliases=("lowes.com",)),
    Company(39, "TJX", "TJX Companies", "Consumer Discretionary", "tjx.com",
            ("about-tjx", "about", "Corporate-Overview")),
    Company(40, "F", "Ford Motor", "Consumer Discretionary", "corporate.ford.com",
            ("us/en/company.html", "", "us/en/who-we-are.html"),
            aliases=("ford.com",)),

    # ---- Energy -----------------------------------------------------------
    Company(41, "XOM", "ExxonMobil", "Energy", "corporate.exxonmobil.com",
            ("who-we-are", "", "about-us"),
            aliases=("exxonmobil.com",)),
    Company(42, "CVX", "Chevron", "Energy", "chevron.com",
            ("about", "who-we-are", "about/our-values")),
    Company(43, "COP", "ConocoPhillips", "Energy", "conocophillips.com",
            ("about-us", "company-reports", "about-us/who-we-are")),
    Company(44, "EOG", "EOG Resources", "Energy", "eogresources.com",
            ("company/about-eog", "about", "company")),
    Company(45, "SLB", "SLB (Schlumberger)", "Energy", "slb.com",
            ("who-we-are", "about", "who-we-are/our-purpose"),
            aliases=("slb.com/about", "schlumberger.com"),
            notes="Rebranded Schlumberger -> SLB in 2022. Pre-2023 snapshots live "
                  "under schlumberger.com. Like Meta, treat the rename as a "
                  "substantive event."),
    Company(46, "MPC", "Marathon Petroleum", "Energy", "marathonpetroleum.com",
            ("about", "who-we-are", "company")),
    Company(47, "PSX", "Phillips 66", "Energy", "phillips66.com",
            ("about", "who-we-are", "about-phillips-66")),
    Company(48, "VLO", "Valero Energy", "Energy", "valero.com",
            ("about-valero", "about", "company")),
    Company(49, "OXY", "Occidental Petroleum", "Energy", "oxy.com",
            ("about-oxy", "about", "who-we-are")),
    Company(50, "HAL", "Halliburton", "Energy", "halliburton.com",
            ("en-US/about-us/corporate-profile/default.page", "en-US/about-us/default.page", "about-us"),
            notes="Halliburton's AEM site uses .page extensions under /en-US/; bare "
                  "/about-us has 0 captures. corporate-profile covers only 2016-2018 "
                  "-> partial, documented coverage."),
)


# Sanity checks that fail fast if the seed list is ever edited inconsistently.
assert len(COMPANIES) == 50, "Sample must contain exactly 50 companies."
assert len({c.ticker for c in COMPANIES}) == 50, "Tickers must be unique."
_SECTOR_COUNTS = {}
for _c in COMPANIES:
    _SECTOR_COUNTS[_c.sector] = _SECTOR_COUNTS.get(_c.sector, 0) + 1
assert all(n == 10 for n in _SECTOR_COUNTS.values()), \
    f"Each sector must have 10 firms; got {_SECTOR_COUNTS}"


def candidate_urls(company: Company) -> list[str]:
    """Full ordered list of candidate URLs to probe for one company.

    Company-specific guesses come first, then a small default set, then the
    same paths against any historical alias domains. Deduplicated, order
    preserved. The collector probes these against CDX and keeps the best.
    """
    seen: set[str] = set()
    urls: list[str] = []

    def add(domain: str, path: str) -> None:
        path = path.lstrip("/")
        url = f"{domain}/{path}" if path else domain
        if url not in seen:
            seen.add(url)
            urls.append(url)

    for p in company.about_paths:
        add(company.domain, p)
    for p in DEFAULT_ABOUT_PATHS:
        add(company.domain, p)
    for alias in company.aliases:
        # An alias may itself include a path (e.g. "slb.com/about").
        if "/" in alias:
            base, _, apath = alias.partition("/")
            add(base, apath)
        else:
            for p in company.about_paths or DEFAULT_ABOUT_PATHS:
                add(alias, p)
    return urls
