"""
Merge a patch run of selected tickers back into the main Part 1 dataset.

Why this exists
---------------
`collect.py --only T1 T2` writes a dataset containing ONLY those tickers, which
would overwrite the full 50-company output. When we need to re-collect a handful
of companies (e.g. ones that came back as throttle-induced false-empties on a
bulk run), we run them into a separate --out-dir and then splice their rows back
into the main dataset with this tool. Rows for the patched tickers are replaced
wholesale; all other companies are left untouched. Company/year order and the
coverage report are regenerated so the merged outputs are indistinguishable from
a single clean run.

    PYTHONPATH=. python -m part1_stated_values.merge \
        --main data/part1 --patch data/part1_patch
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from config.companies import COMPANIES
from part1_stated_values.collect import COLUMNS, coverage_report


def main() -> None:
    ap = argparse.ArgumentParser(description="Splice a patch collection into the main Part 1 dataset.")
    ap.add_argument("--main", default="data/part1", type=Path)
    ap.add_argument("--patch", required=True, type=Path)
    args = ap.parse_args()

    main = pd.read_csv(args.main / "part1_stated_values.csv")
    patch = pd.read_csv(args.patch / "part1_stated_values.csv")
    tickers = sorted(patch["ticker"].unique())
    print("patch tickers:", tickers)

    merged = pd.concat([main[~main["ticker"].isin(tickers)], patch], ignore_index=True)

    # Restore the canonical sample order (sector blocks, then year) so the merged
    # file matches a clean full run.
    order = {c.ticker: i for i, c in enumerate(COMPANIES)}
    merged["_o"] = merged["ticker"].map(order)
    merged = merged.sort_values(["_o", "year"]).drop(columns="_o")[COLUMNS]

    merged.to_csv(args.main / "part1_stated_values.csv", index=False)
    merged.to_parquet(args.main / "part1_stated_values.parquet", index=False)
    coverage_report(merged).to_csv(args.main / "part1_coverage_report.csv", index=False)

    usable = (merged["coverage_status"] == "ok").sum()
    print(f"merged: {len(merged)} rows, {usable} usable ({100*usable/max(len(merged),1):.0f}%)")
    for tk in tickers:
        g = merged[merged["ticker"] == tk]
        print(f"  {tk:6} usable={ (g['coverage_status']=='ok').sum() }/9  "
              f"statuses={g['coverage_status'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
