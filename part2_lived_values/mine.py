"""
Part 2 text mining: turn each SEC proxy statement (DEF 14A) into a structured,
comparable row. Documents are sourced from EDGAR (see edgar.py).

Two layers, by design:

  CLASSICAL (primary, cheap, fully scalable, transparent)
    * topic emphasis — a 10-dim vector over the SAME value categories as Part 1,
      via the seed lexicons. This vector is the backbone of Part 3 alignment.
    * tone — Loughran-McDonald positive / negative / uncertainty / litigious
      proportions + a net-tone score (the standard for disclosure text).
    * readability — approximate Flesch Reading Ease (a boilerplate/complexity proxy).
    * within-company change — cosine distance between consecutive years' emphasis
      vectors, and % change in length.

  LLM (optional, --use-llm, interpretive)
    * commitment "concreteness" and forward-vs-backward orientation on the filing's
      front matter (proxy summary / letter), where authenticity-relevant framing
      concentrates. Cached on disk.

Why this split: a dictionary emphasis vector over a long filing is cheap,
reproducible, and directly comparable to Part 1's themes — so it carries the
cross-company / cross-sector / over-time analysis the brief asks for. The LLM
adds qualitative signal (vague aspiration vs. quantified commitment) without
being on the critical path or blowing up token cost.

    python -m part2_lived_values.mine --out-dir data/part2 [--use-llm] \
        [--lm-dict path/to/LoughranMcDonald_MasterDictionary.csv] \
        --user-agent "Your Name research (you@example.com)"   # SEC etiquette
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import re
from pathlib import Path

import pandas as pd

from config.companies import COMPANIES
from part1_stated_values.analyze import TAXONOMY
from part1_stated_values.collect import build_session
from part2_lived_values import edgar, extract_filing, lexicons

log = logging.getLogger("part2.mine")

CATS = list(TAXONOMY.keys())   # fixed category order for every vector/column
_WORD_RE = re.compile(r"[a-z][a-z'-]+")
_LLM_FRONT_CHARS = 8000


# --------------------------- classical metrics -----------------------------
def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def category_counts(text: str) -> dict[str, int]:
    """Count lexicon hits per category over the lowercased text."""
    low = text.lower()
    counts = {c: 0 for c in CATS}
    for cat, terms in lexicons.CATEGORY_LEXICONS.items():
        total = 0
        for term in terms:
            if " " in term or "-" in term:        # phrase: substring count
                total += low.count(term)
            else:                                  # single stem: word-prefix
                total += len(re.findall(rf"\b{re.escape(term)}\w*", low))
        counts[cat] = total
    return counts


def emphasis_share(counts: dict[str, int]) -> dict[str, float]:
    """Normalize category counts into shares summing to 1 (0s if no hits)."""
    total = sum(counts.values())
    if total == 0:
        return {c: 0.0 for c in CATS}
    return {c: round(counts[c] / total, 4) for c in CATS}


def lm_tone(tokens: list[str], lm: dict[str, set[str]]) -> dict[str, float]:
    n = max(len(tokens), 1)
    counts = {k: sum(1 for t in tokens if t in words) for k, words in lm.items()}
    props = {f"lm_{k}": round(v / n, 5) for k, v in counts.items()}
    pos, neg = counts.get("positive", 0), counts.get("negative", 0)
    props["net_tone"] = round((pos - neg) / (pos + neg + 1e-9), 4)
    return props


def _syllables(word: str) -> int:
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups)
    if word.endswith("e") and n > 1:
        n -= 1
    return max(n, 1)


def flesch_reading_ease(text: str, tokens: list[str]) -> float:
    """Approximate Flesch Reading Ease. Higher = easier. Documented as an estimate."""
    sentences = max(len(re.findall(r"[.!?]+", text)), 1)
    words = max(len(tokens), 1)
    syll = sum(_syllables(t) for t in tokens)
    score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syll / words)
    return round(score, 1)


def cosine_distance(a: dict[str, float], b: dict[str, float]) -> float | None:
    va = [a[c] for c in CATS]
    vb = [b[c] for c in CATS]
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(x * x for x in vb))
    if na == 0 or nb == 0:
        return None
    cos = sum(x * y for x, y in zip(va, vb)) / (na * nb)
    return round(1 - cos, 4)


# --------------------------- optional LLM layer -----------------------------
_LLM_SYSTEM = (
    "You are coding the framing of a corporate sustainability/ESG report from its "
    "front matter (CEO letter / executive summary). Return ONLY JSON:\n"
    '{"concreteness": <0..1>, "forward_orientation": <0..1>, "note": "<one sentence>"}\n'
    "concreteness: 0 = vague aspiration, 1 = specific, quantified, time-bound "
    "commitments. forward_orientation: 0 = mostly past achievements, 1 = mostly "
    "future targets. note: one sentence on the report's dominant rhetorical stance."
)


def llm_commitment(text: str, client, cache_dir: Path) -> dict:
    excerpt = text[:_LLM_FRONT_CHARS]
    key = hashlib.sha1(f"{excerpt}|{client.model}".encode()).hexdigest()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cpath = cache_dir / f"{key}.json"
    if cpath.exists():
        return json.loads(cpath.read_text())
    try:
        result = client.complete_json(_LLM_SYSTEM, f"FRONT MATTER:\n{excerpt}")
    except Exception as exc:
        log.warning("LLM commitment coding failed: %s", exc)
        return {"concreteness": None, "forward_orientation": None, "note": "LLM_ERROR"}
    cpath.write_text(json.dumps(result))
    return result


# ------------------------------ orchestration -------------------------------
def _file_sha1(path: str) -> str:
    """SHA1 of a file's raw bytes — used to catch a filing duplicated across years."""
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mine_company(company, refs, session, *, cache_dir: Path, lm, use_llm: bool,
                 llm_client, llm_cache: Path) -> list[dict]:
    rows, prev_share, prev_words = [], None, None
    seen_hashes: dict[str, int] = {}   # document content hash -> first year it appeared
    for ref in refs:
        edgar.download(ref, session, cache_dir)
        base = dict(ticker=company.ticker, company_name=company.name,
                    sector=company.sector, year=ref.year,
                    report_url=ref.url, report_source=ref.source)

        if ref.status in ("", "not_found"):
            rows.append({**base, "coverage_status": "not_found"})
            prev_share = None  # don't bridge a gap for the shift metric
            continue
        if ref.status == "download_failed":
            rows.append({**base, "coverage_status": "download_failed"})
            prev_share = None
            continue

        # Defensive de-duplication: if the same document is served for two years
        # (byte-identical), it is not a genuine datapoint for the later year, so we
        # record an explicit gap pointing at the year it duplicates rather than
        # double-counting stale content into the emphasis/tone series.
        digest = _file_sha1(ref.local_path)
        if digest in seen_hashes:
            rows.append({**base, "coverage_status": "duplicate_of_prior",
                         "duplicate_of_year": seen_hashes[digest]})
            prev_share = None
            continue
        seen_hashes[digest] = ref.year

        text, n_pages, ext_status = extract_filing.extract_text(ref.local_path)
        if ext_status != "ok":
            rows.append({**base, "n_pages": n_pages, "coverage_status": ext_status})
            prev_share = None
            continue

        tokens = tokenize(text)
        counts = category_counts(text)
        share = emphasis_share(counts)
        tone = lm_tone(tokens, lm)
        row = {
            **base, "n_pages": n_pages, "n_words": len(tokens),
            "extract_status": ext_status,
            **{f"emphasis_{c}": share[c] for c in CATS},
            "top_category": max(share, key=share.get) if sum(counts.values()) else "",
            **tone,
            "flesch": flesch_reading_ease(text, tokens),
            "emphasis_shift_cosine": cosine_distance(prev_share, share) if prev_share else None,
            "word_count_delta_pct": (round(100 * (len(tokens) - prev_words) / prev_words, 1)
                                     if prev_words else None),
            "coverage_status": "ok",
        }
        if use_llm:
            c = llm_commitment(text, llm_client, llm_cache)
            row["llm_concreteness"] = c.get("concreteness")
            row["llm_forward_orientation"] = c.get("forward_orientation")
            row["llm_note"] = (c.get("note") or "").strip()
        rows.append(row)
        prev_share, prev_words = share, len(tokens)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Part 2 lived-values text mining (SEC proxy statements via EDGAR).")
    ap.add_argument("--out-dir", default="data/part2", type=Path)
    ap.add_argument("--edgar-cache", default="data/part2/_edgar_cache", type=Path)
    ap.add_argument("--llm-cache", default="data/part2/_llm_cache", type=Path)
    ap.add_argument("--from-year", default=2016, type=int)
    ap.add_argument("--to-year", default=2024, type=int)
    ap.add_argument("--lm-dict", default=None, help="path to LM Master Dictionary CSV")
    ap.add_argument("--use-llm", action="store_true", help="run the LLM commitment layer")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--user-agent",
                    default="Wharton-TAU-Lab research RA task (academic; contact: you@example.com)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session = build_session(args.user_agent)
    lm = lexicons.load_lm_dictionary(args.lm_dict)

    llm_client = None
    if args.use_llm:
        from common.llm import OpenAIClient
        llm_client = OpenAIClient()

    companies = list(COMPANIES)
    if args.only:
        want = {t.upper() for t in args.only}
        companies = [c for c in companies if c.ticker.upper() in want]
    if args.limit:
        companies = companies[: args.limit]

    all_rows = []
    for c in companies:
        log.info("[%s] %s", c.ticker, c.name)
        refs = edgar.resolve_company(c, session, args.from_year, args.to_year)
        all_rows.extend(mine_company(
            c, refs, session, cache_dir=args.edgar_cache, lm=lm,
            use_llm=args.use_llm, llm_client=llm_client, llm_cache=args.llm_cache))

    df = pd.DataFrame(all_rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_dir / "part2_lived_values.csv", index=False)
    df.to_parquet(args.out_dir / "part2_lived_values.parquet", index=False)

    # coverage report
    cov = (df.groupby(["sector", "ticker"])["coverage_status"]
             .apply(lambda s: (s == "ok").sum()).reset_index(name="years_ok"))
    cov.to_csv(args.out_dir / "part2_coverage_report.csv", index=False)

    ok = (df["coverage_status"] == "ok").sum()
    log.info("\nDone. %d company-years, %d usable reports. Wrote to %s",
             len(df), ok, args.out_dir)


if __name__ == "__main__":
    main()
