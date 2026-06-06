"""
Lexicons for the classical text-mining layer.

Two dictionaries:

1. CATEGORY_LEXICONS — seed term lists for the SAME 10 value categories used in
   Part 1 (imported from part1's taxonomy so the two parts can never drift). This
   is what makes a report's "topic emphasis" directly comparable to the company's
   stated values, which is the whole basis of the Part 3 alignment measure.
   These are hand-authored seed lists: transparent, editable, and meant to be
   expanded after inspecting real reports. They are matched as word-stem prefixes
   (so "innovat" catches innovation/innovative/innovating).

2. Loughran-McDonald (LM) finance sentiment dictionary — the standard tool for
   tone in corporate disclosure text. The full Master Dictionary is a large
   external file we do NOT bundle; `load_lm_dictionary()` loads it from a path you
   provide. Without it, a small clearly-labelled fallback keeps the pipeline
   runnable (but the README flags that real results need the genuine LM file).
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from part1_stated_values.analyze import TAXONOMY  # the 10 categories, single source

log = logging.getLogger("part2.lexicons")

# Stem-prefix seed terms per value category. Keys exactly match Part 1's TAXONOMY.
CATEGORY_LEXICONS: dict[str, tuple[str, ...]] = {
    "innovation_technology": (
        "innovat", "research", "develop", "technolog", "patent", "digital",
        "invent", "breakthrough", "cutting-edge", "pioneer", "disrupt", "ai "),
    "customer_focus": (
        "customer", "client", "consumer", "patient experience", "service qualit",
        "satisfaction", "user ", "member experience"),
    "integrity_ethics": (
        "integrity", "ethic", "complian", "governance", "transparen", "accountab",
        "anti-corrupt", "code of conduct", "honest", "trust", "bribery"),
    "people_talent": (
        "employee", "talent", "workforce", "well-being", "wellbeing", "training",
        "develop our people", "culture", "engagement", "retention", "colleague"),
    "diversity_inclusion": (
        "divers", "inclusi", "equity", "belonging", "represent", "gender",
        "minorit", "underrepresent", "pay equit", "equal opportun"),
    "sustainability_environment": (
        "sustainab", "emission", "carbon", "climate", "greenhouse", "renewable",
        "net-zero", "net zero", "biodivers", "water ", "waste", "environment"),
    "community_social_impact": (
        "communit", "philanthrop", "donat", "volunteer", "social impact",
        "access to", "underserved", "charit", "foundation grant"),
    "financial_growth_shareholder": (
        "shareholder", "profit", "revenue growth", "return on", "earnings",
        "value creation", "margin", "capital allocation", "dividend", "scale"),
    "quality_excellence": (
        "quality", "safety", "reliab", "excellence", "operational", "standard",
        "defect", "incident rate", "craftsmanship", "rigor"),
    "global_scale_reach": (
        "global", "worldwide", "international", "across the world", "countries",
        "footprint", "presence in", "markets around"),
}

assert set(CATEGORY_LEXICONS) == set(TAXONOMY), \
    "Category lexicons must cover exactly the Part 1 taxonomy categories."

# Minimal fallback tone lists — NOT the real LM dictionary, only enough to keep
# the pipeline runnable. README flags that genuine results require the LM file.
_FALLBACK_LM: dict[str, set[str]] = {
    "positive": {"achieve", "improve", "strong", "progress", "success", "leading",
                 "advance", "benefit", "opportunity", "gain", "excellent"},
    "negative": {"risk", "loss", "decline", "fail", "concern", "adverse",
                 "violation", "penalty", "harm", "weak", "litigation"},
    "uncertainty": {"may", "could", "approximately", "uncertain", "possibly",
                    "depend", "believe", "estimate", "assume", "risk"},
    "litigious": {"litigation", "lawsuit", "regulation", "compliance", "statute",
                  "liable", "plaintiff", "settlement"},
}


def load_lm_dictionary(path: str | Path | None) -> dict[str, set[str]]:
    """Load LM tone word sets from the Master Dictionary CSV at `path`.

    The LM Master Dictionary marks each word with the first year it appears in a
    given sentiment list (0 = not in list). We treat any non-zero year as
    membership. If `path` is missing, return the labelled fallback.
    """
    if not path or not Path(path).exists():
        log.warning("LM dictionary not found at %r — using minimal FALLBACK lists. "
                    "Download the real Master Dictionary for valid tone results.", path)
        return _FALLBACK_LM

    cols = {"positive": "Positive", "negative": "Negative",
            "uncertainty": "Uncertainty", "litigious": "Litigious"}
    out: dict[str, set[str]] = {k: set() for k in cols}
    with open(path, newline="", encoding="utf-8", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            word = (row.get("Word") or "").strip().lower()
            if not word:
                continue
            for key, col in cols.items():
                val = row.get(col, "0")
                if val and val not in ("0", "", "0.0"):
                    out[key].add(word)
    log.info("Loaded LM dictionary: " +
             ", ".join(f"{k}={len(v)}" for k, v in out.items()))
    return out
