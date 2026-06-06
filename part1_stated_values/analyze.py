"""
Part 1 LLM analysis pass.

Reads the cleaned snapshot dataset from collect.py and fills the two interpretive
columns the brief asks for:
    theme_categories  -> which value categories the page expresses, with salience
    analyst_notes     -> a one-line note on the notable linguistic shift vs. prior year

    python -m part1_stated_values.analyze \
        --in  data/part1/part1_stated_values.parquet \
        --out data/part1/part1_stated_values_analyzed.parquet

Provider: OpenAI by default. The LLM is reached through a tiny `LLMClient`
abstraction, so switching providers (or models) is a one-class change and never
touches the orchestration logic.

Cost discipline (all documented choices):
  * The model is only called for rows with usable text (`coverage_status == ok`).
  * If a year's normalized text is byte-identical to the prior year
    (`similarity_to_prior == 1.0`), we REUSE the prior themes and skip the call —
    identical text cannot have different themes.
  * The expensive shift note is only generated when the deterministic detector
    from extract.py says the page actually changed; otherwise it's a fixed string.
  * Every call is cached on disk keyed by (text hash, prior-text hash, taxonomy
    version, model), so re-runs and tuning passes are free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

import pandas as pd

from common.llm import LLMClient, OpenAIClient  # shared, provider-swappable client

log = logging.getLogger("part1.analyze")

# ---------------------------------------------------------------------------
# Value taxonomy  (the central judgment call of Part 1 — justified below)
# ---------------------------------------------------------------------------
#
# Design goals for the categories:
#   1. SECTOR-NEUTRAL. The same scheme must apply to a bank and an oil major so
#      cross-sector comparison is meaningful. We avoid industry-specific labels.
#   2. BRIDGES TO PART 2. The "stated" themes are deliberately chosen to map onto
#      the Environmental / Social / Governance / Business-performance dimensions
#      that the Part 2 disclosure analysis measures. That mapping is what lets
#      Part 3 compute say-vs-do *alignment* on a common footing rather than
#      comparing two incommensurable vocabularies.
#   3. MUTUALLY INTELLIGIBLE, not mutually exclusive. A page can (and usually
#      does) express several; we score salience per category rather than forcing
#      one label.
#
# ESG bridge (documented for Part 3):
#   Environmental -> sustainability_environment
#   Social        -> people_talent, diversity_inclusion, community_social_impact,
#                    customer_focus
#   Governance    -> integrity_ethics
#   Business/Perf -> innovation_technology, financial_growth_shareholder,
#                    quality_excellence, global_scale_reach
#
# Bump TAXONOMY_VERSION whenever the categories or their definitions change; it
# is part of the cache key so stale codings are never silently reused.
TAXONOMY_VERSION = "v1"

TAXONOMY: dict[str, str] = {
    "innovation_technology":
        "R&D, invention, technological leadership, being cutting-edge or disruptive.",
    "customer_focus":
        "Serving, delighting, or being obsessed with customers; service quality.",
    "integrity_ethics":
        "Honesty, ethics, trust, transparency, accountability, governance.",
    "people_talent":
        "Employees, talent, development, wellbeing, culture, being a great workplace.",
    "diversity_inclusion":
        "Diversity, equity, inclusion, belonging, representation.",
    "sustainability_environment":
        "Climate, emissions, energy transition, environmental stewardship, net-zero.",
    "community_social_impact":
        "Communities, philanthropy, social responsibility, broadening access.",
    "financial_growth_shareholder":
        "Growth, profitability, shareholder value, returns, scale as a goal.",
    "quality_excellence":
        "Quality, operational excellence, reliability, craftsmanship, and safety.",
    "global_scale_reach":
        "Global presence/reach; serving the world; the scale of operations.",
}

_NO_CHANGE_NOTE = "No substantive change in stated-values text from the prior year."
_FIRST_YEAR_NOTE = "First observed year; no prior-year text to compare against."

# Long pages are truncated before the LLM call. About/values pages are short;
# this guards against an occasional over-captured page inflating token cost.
_MAX_CHARS = 6000


# ---------------------------------------------------------------------------
# Prompt construction (the LLM client itself lives in common/llm.py)
# ---------------------------------------------------------------------------
def build_system_prompt() -> str:
    cats = "\n".join(f"- {name}: {desc}" for name, desc in TAXONOMY.items())
    return (
        "You are a careful research assistant coding the values language of "
        "corporate 'About Us' / mission / values web pages for an academic study.\n\n"
        "Score how salient each of these value categories is in the CURRENT-YEAR "
        "text, from 0.0 (absent) to 1.0 (a dominant theme of the page):\n"
        f"{cats}\n\n"
        "If PRIOR-YEAR text is provided, also write ONE concise sentence naming "
        "the single most notable linguistic shift from prior to current (e.g. a "
        "new emphasis, a dropped theme, a tonal change). If the change is "
        "trivial, say so.\n\n"
        "Respond with ONLY a JSON object, no prose, in exactly this shape:\n"
        '{"themes": {"<category>": <float 0..1>, ...}, "shift_note": "<one sentence>"}\n'
        "Include only categories with salience > 0. Use only the category names "
        "listed above."
    )


def build_user_prompt(curr_text: str, prior_text: str | None) -> str:
    curr = curr_text[:_MAX_CHARS]
    prior = (prior_text or "")[:_MAX_CHARS] if prior_text else "N/A"
    return f"CURRENT-YEAR TEXT:\n{curr}\n\nPRIOR-YEAR TEXT (for shift comparison):\n{prior}"


def _clean_themes(raw: dict) -> dict[str, float]:
    """Keep only valid taxonomy keys with sane 0..1 salience values."""
    out: dict[str, float] = {}
    for k, v in (raw or {}).items():
        if k in TAXONOMY:
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            if f > 0:
                out[k] = round(min(max(f, 0.0), 1.0), 3)
    return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _cache_key(curr_norm_sha1: str, prior_norm_sha1: str, model: str) -> str:
    raw = f"{curr_norm_sha1}|{prior_norm_sha1}|{TAXONOMY_VERSION}|{model}"
    return hashlib.sha1(raw.encode()).hexdigest()


def _load_cache(cache_dir: Path, key: str) -> dict | None:
    p = cache_dir / f"{key}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def _save_cache(cache_dir: Path, key: str, value: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(json.dumps(value))


def analyze(df: pd.DataFrame, client: LLMClient, cache_dir: Path,
            model_name: str) -> pd.DataFrame:
    system = build_system_prompt()
    out = df.copy()

    # Process company by company in year order so prior-year context is correct.
    out = out.sort_values(["ticker", "year"]).reset_index(drop=True)

    # The collection step emits these two columns empty, so they load back as
    # all-NaN float64. (Re)create them as string columns up front: pandas >=2.1
    # raises on assigning a str into a float64 cell rather than upcasting, and the
    # fill loop below writes strings into every row.
    out["theme_categories"] = ""
    out["analyst_notes"] = ""

    api_calls = 0
    prev_by_ticker: dict[str, dict] = {}  # ticker -> {"text":..., "themes":..., "sha1":...}

    for i, row in out.iterrows():
        ticker = row["ticker"]
        if row["coverage_status"] != "ok":
            # Gaps/thin text get no coding; leave the interpretive columns empty.
            out.at[i, "theme_categories"] = ""
            out.at[i, "analyst_notes"] = ""
            prev_by_ticker.pop(ticker, None)  # don't bridge a gap for shift notes
            continue

        curr_text = row["page_text_clean"] or ""
        curr_sha1 = row["text_sha1"] or hashlib.sha1(curr_text.encode()).hexdigest()
        prev = prev_by_ticker.get(ticker)

        # Fast path: text identical to prior year -> reuse themes, no API call.
        if prev and row["similarity_to_prior"] == 1.0:
            themes = prev["themes"]
            note = _NO_CHANGE_NOTE
        else:
            prior_text = prev["text"] if prev else None
            prior_sha1 = prev["sha1"] if prev else ""
            key = _cache_key(curr_sha1, prior_sha1, model_name)
            cached = _load_cache(cache_dir, key)
            if cached is not None:
                result = cached
            else:
                user = build_user_prompt(curr_text, prior_text)
                try:
                    result = client.complete_json(system, user)
                    api_calls += 1
                    _save_cache(cache_dir, key, result)
                except Exception as exc:  # never let one bad row kill the run
                    log.warning("LLM call failed for %s %s: %s",
                                ticker, row["year"], exc)
                    result = {"themes": {}, "shift_note": "LLM_ERROR"}
            themes = _clean_themes(result.get("themes", {}))
            note = (result.get("shift_note") or "").strip()
            if prev is None:
                note = _FIRST_YEAR_NOTE
            elif not note:
                note = _NO_CHANGE_NOTE

        out.at[i, "theme_categories"] = json.dumps(themes)
        out.at[i, "analyst_notes"] = note
        prev_by_ticker[ticker] = {"text": curr_text, "themes": themes, "sha1": curr_sha1}

    log.info("Analysis complete. LLM calls made this run: %d (rest cached/reused).",
             api_calls)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="LLM theme/shift analysis for Part 1.")
    ap.add_argument("--in", dest="infile", default="data/part1/part1_stated_values.parquet")
    ap.add_argument("--out", dest="outfile",
                    default="data/part1/part1_stated_values_analyzed.parquet")
    ap.add_argument("--cache-dir", default="data/part1/_llm_cache", type=Path)
    ap.add_argument("--model", default=None,
                    help="LLM model name; defaults to $OPENAI_MODEL or gpt-4o-mini")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    infile = Path(args.infile)
    df = pd.read_parquet(infile) if infile.suffix == ".parquet" else pd.read_csv(infile)

    client = OpenAIClient(model=args.model)
    result = analyze(df, client, args.cache_dir, client.model)

    outpath = Path(args.outfile)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    if outpath.suffix == ".parquet":
        result.to_parquet(outpath, index=False)
        result.to_csv(outpath.with_suffix(".csv"), index=False)
    else:
        result.to_csv(outpath, index=False)
    log.info("Wrote analyzed dataset to %s", outpath)


if __name__ == "__main__":
    main()
