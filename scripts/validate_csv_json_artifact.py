#!/usr/bin/env python3
"""Validate a UTF-8-BOM CSV dataset and atomically write an equivalent JSON list.

This is intentionally transport-free: it validates an already collected public
artifact without making network requests.  It is used to make legacy weekly
CSV-only results conform to the CSV/JSON publication contract.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        fields = list(reader.fieldnames)
        rows = [{field: row.get(field, "") for field in fields} for row in reader]
    if not rows:
        raise ValueError("CSV has no data rows")
    if any(set(row) - set(fields) for row in rows):
        raise ValueError("CSV row contains an unexpected field")
    return fields, rows


def validate(fields: list[str], rows: list[dict[str, str]], stable_id: str, name: str, expected_total: int) -> None:
    if stable_id not in fields or name not in fields:
        raise ValueError(f"required field missing: stable_id={stable_id!r} name={name!r}")
    if len(rows) != expected_total:
        raise ValueError(f"count mismatch: rows={len(rows)} reported_total={expected_total}")
    missing_names = [index + 2 for index, row in enumerate(rows) if not row.get(name, "").strip()]
    if missing_names:
        raise ValueError(f"missing required names at CSV records {missing_names[:8]}")
    ids = [row.get(stable_id, "").strip() for row in rows]
    duplicates = [key for key, count in Counter(ids).items() if not key or count > 1]
    if duplicates:
        raise ValueError(f"missing or duplicate stable IDs: {duplicates[:8]}")
    for row in rows:
        detail = row.get("detail_page_url", "")
        if detail and not detail.startswith("https://"):
            raise ValueError(f"non-HTTPS detail URL: {detail!r}")


def write_json(path: Path, fields: list[str], rows: list[dict[str, str]], source_csv: Path, reported_total: int) -> None:
    payload = {
        "source_csv": source_csv.name,
        "reported_total": reported_total,
        "field_order": fields,
        "records": [{field: row.get(field, "") for field in fields} for row in rows],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def read_back(csv_path: Path, json_path: Path) -> None:
    fields, rows = load_csv(csv_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("field_order") != fields or payload.get("records") != [{field: row.get(field, "") for field in fields} for row in rows]:
        raise ValueError("CSV/JSON read-back mismatch")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--stable-id", required=True)
    parser.add_argument("--name-field", required=True)
    parser.add_argument("--reported-total", type=int, required=True)
    args = parser.parse_args()
    fields, rows = load_csv(args.csv)
    validate(fields, rows, args.stable_id, args.name_field, args.reported_total)
    write_json(args.json_output, fields, rows, args.csv, args.reported_total)
    read_back(args.csv, args.json_output)
    print(f"validated rows={len(rows)} csv={args.csv} json={args.json_output}")


if __name__ == "__main__":
    main()
