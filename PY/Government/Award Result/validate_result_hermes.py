#!/usr/bin/env python3
"""Validate a Hermes government-contract dry-run result and its audit trail."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "ref", "department", "description", "awardee", "award_date",
    "sum", "period", "url", "start", "end",
]
CORE_COLUMNS = ["department", "awardee", "sum", "url"]


def nonempty_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    manifest = json.loads((args.run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "completed":
        errors.append(f"manifest status is {manifest.get('status')!r}")
    extractor_names = {
        "epd", "dsd", "cedd", "cedd_consultant", "emsd_award",
        "emsd_construction", "hkaa", "hyd", "wsd", "wsd_consultant", "td", "gld",
    }
    latest: dict[str, dict] = {}
    for stage in manifest.get("stages", []):
        latest[stage["name"]] = stage
    for name in extractor_names | {"normalize_unstructured", "format"}:
        if latest.get(name, {}).get("status") != "passed":
            errors.append(f"latest stage {name!r} did not pass")

    rejects = args.run_dir / "Raw" / "data" / "normalization_rejects.json"
    if not rejects.is_file() or nonempty_lines(rejects) != 0:
        errors.append("normalization rejects are non-empty or absent")

    frame = pd.read_csv(args.csv)
    if list(frame.columns) != EXPECTED_COLUMNS:
        errors.append(f"unexpected columns: {list(frame.columns)!r}")
    if frame.empty:
        errors.append("CSV is empty")
    if frame.duplicated().any():
        errors.append(f"CSV has {int(frame.duplicated().sum())} exact duplicates")
    for column in CORE_COLUMNS:
        empty = frame[column].isna() | frame[column].fillna("").astype(str).str.strip().eq("")
        if empty.any():
            errors.append(f"{column} has {int(empty.sum())} empty values")
    for column in ("ref", "description"):
        empty = frame[column].isna() | frame[column].fillna("").astype(str).str.strip().eq("")
        if empty.any():
            warnings.append(f"source omitted {column} in {int(empty.sum())} Transport rows")
    substantive_empty = frame[["ref", "description", "awardee", "sum"]].isna().all(axis=1)
    if substantive_empty.any():
        errors.append(f"CSV has {int(substantive_empty.sum())} rows with no substantive contract fields")
    nonempty_dates = frame["award_date"].dropna().astype(str).str.strip()
    invalid_dates = pd.to_datetime(nonempty_dates, errors="coerce").isna()
    if invalid_dates.any():
        errors.append(f"award_date has {int(invalid_dates.sum())} invalid non-empty values")
    missing_date_departments = set(frame.loc[frame["award_date"].isna(), "department"])
    if missing_date_departments - {"Water Supplies Department"}:
        errors.append(f"unexpected departments with missing dates: {sorted(missing_date_departments)!r}")
    if frame["award_date"].isna().any():
        warnings.append(
            f"WSD consultancy source omitted award_date in {int(frame['award_date'].isna().sum())} rows"
        )
    non_https = ~frame["url"].astype(str).str.startswith("https://")
    if non_https.any():
        errors.append(f"URL has {int(non_https.sum())} non-HTTPS values")
    max_field_length = max(int(frame[column].fillna("").astype(str).str.len().max()) for column in frame.columns)
    if max_field_length > 10_000:
        errors.append(f"suspicious expanded field length: {max_field_length}")
    if args.csv.stat().st_size > 10 * 1024 * 1024:
        errors.append(f"suspicious CSV size: {args.csv.stat().st_size}")

    summary = {
        "status": "PASS" if not errors else "FAIL",
        "rows": len(frame),
        "columns": list(frame.columns),
        "exact_duplicates": int(frame.duplicated().sum()),
        "missing_award_dates": int(frame["award_date"].isna().sum()),
        "date_min": str(pd.to_datetime(nonempty_dates).min()),
        "date_max": str(pd.to_datetime(nonempty_dates).max()),
        "transport_rows": int(frame["department"].eq("Transport Department").sum()),
        "normalization_rejects": nonempty_lines(rejects) if rejects.is_file() else None,
        "max_field_length": max_field_length,
        "csv_size": args.csv.stat().st_size,
        "warnings": warnings,
        "errors": errors,
    }
    rendered = json.dumps(summary, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
