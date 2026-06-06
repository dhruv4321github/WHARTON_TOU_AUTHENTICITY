# CLAUDE.md — working instructions for this repo

Concise on purpose. Full task context is imported below; this file is the
durable instruction layer Claude Code loads every session.

## Context (read these)
- @docs/ASSIGNMENT.md — the verbatim recruitment brief (all 4 parts)
- @README.md — repo layout + how the parts connect
- @part1_stated_values/README.md — Part 1 decisions, schema, limitations

## What this project is
A scoped proof-of-concept measuring the gap between what 50 large firms *say*
they value (Part 1, Wayback "About Us" pages) and what their disclosures
*suggest* they prioritize (Part 2, ESG/DEI/proxy text), combined into an
authenticity index (Part 3), plus one exploratory analysis (Part 4).
The sample is 50 firms but **all methods must scale to the full S&P 500.**

## Hard conventions
- **Document every judgment call at the point of decision** — in code comments
  and per-part READMEs. A well-justified imperfect choice beats an unjustified
  one. This is graded directly.
- Keep the deterministic/cheap work out of the LLM (e.g. change-detection,
  coverage status); reserve the LLM for interpretive questions (themes, shifts).
- Gaps are recorded explicitly, never silently filled. Optimize for honest,
  documented coverage over fabricated completeness.
- Python 3.11+, type hints, `dataclasses` for records. Run modules with
  `PYTHONPATH=.` from repo root. New deps go in `requirements.txt`.
- Don't re-hit external services on re-runs: cache fetched HTML/PDFs to disk
  keyed by a stable id, as `collect.py` already does.
- `config/companies.py` is the single source of truth for the sample. Never
  hardcode the 50 elsewhere.

## Workflow expectations
- Propose a short plan before large changes; I review code as it lands.
- Each part ships: code + a per-part README + output data + a 1–2pp written
  summary for a non-technical reader.

## LLM provider
OpenAI. Shared client lives in `common/llm.py` (`OpenAIClient`), used by both
Part 1 and Part 2 — swapping providers/models is a one-class change. Set
`OPENAI_API_KEY`; model defaults to `$OPENAI_MODEL` or `gpt-4o-mini` (override
with `--model` or the env var).

## Status / next steps
- ✅ Part 1 — stated values: collection (`cdx/extract/collect`) + LLM theme/shift
  analysis (`analyze.py`, 10-category taxonomy, OpenAI). Run on all 50 (328/450
  usable, 73%); `SUMMARY.md` written. Adds `--cdx-timeout` + `merge.py` for re-runs.
- ✅ Part 2 — lived values: **proxy statements (DEF 14A) via SEC EDGAR** (`edgar.py`
  resolve/download + `extract_filing.py`; `lexicons.py` + `mine.py` for emphasis
  vector, LM tone, Flesch, YoY cosine shift, dedup guard, optional LLM). Run on all
  50 (442/450 usable, 98%); `SUMMARY.md` written. (Chosen over voluntary
  ESG/sustainability reports for coverage and sourcing reliability.)
- ▶️ Next: Part 3 authenticity index (Part 1 stated themes vs Part 2 emphasis
  vectors on the shared 10-category space); Part 4.
