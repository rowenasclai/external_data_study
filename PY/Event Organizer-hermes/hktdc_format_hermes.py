#!/usr/bin/env python3
"""Deterministically format aligned HKTDC Hermes L1/L2/L3 artifacts."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "Result" / "Exhibition Organizers" / "HKTDC"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def atomic_write(path: Path, content: str, encoding: str) -> None:
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temp_path = Path(temporary.name)
    temp_path.replace(path)


def prefixed(prefix: str, row: dict[str, str]) -> dict[str, str]:
    return {f"{prefix}{key.lower().replace(' ', '_').replace('/', '_')}": value for key, value in row.items()}


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def format_records(prefix: str) -> list[dict[str, str]]:
    directory = OUTPUT_ROOT / prefix
    l1 = read_csv(directory / f"hktdc_{prefix}_L1.csv")
    l2 = read_csv(directory / f"hktdc_{prefix}_L2.csv")
    l3 = read_csv(directory / f"hktdc_{prefix}_L3.csv")
    if not l1 or len(l1) != len(l2) or len(l1) != len(l3):
        raise ValueError(f"alignment failure: L1={len(l1)}, L2={len(l2)}, L3={len(l3)}")
    records = []
    for position, (one, two, three) in enumerate(zip(l1, l2, l3), start=1):
        if canonical_url(two.get("exhibitor_url", "")) != canonical_url(one.get("url", "")):
            raise ValueError(f"position {position}: L1/L2 exhibitor URL mismatch")
        record = {"source_position": str(position), **prefixed("l1_", one), **prefixed("l2_", two), **prefixed("l3_", three)}
        records.append(record)
    return records


def write_outputs(prefix: str, records: list[dict[str, str]]) -> tuple[Path, Path]:
    directory = OUTPUT_ROOT / prefix
    fields = list(dict.fromkeys(key for row in records for key in row))
    normalized = [{key: row.get(key, "") for key in fields} for row in records]
    json_path = directory / f"imp_hktdc_{prefix}_hermes.json"
    csv_path = directory / f"imp_hktdc_{prefix}_hermes.csv"
    atomic_write(json_path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in normalized), "utf-8")
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows(normalized)
    atomic_write(csv_path, buffer.getvalue(), "utf-8-sig")
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    records = format_records(args.prefix)
    json_path, csv_path = write_outputs(args.prefix, records)
    json_rows = [json.loads(line) for line in json_path.read_text(encoding="utf-8").splitlines()]
    csv_rows = read_csv(csv_path)
    if records != json_rows or records != csv_rows:
        raise ValueError("formatted CSV/JSON read-back equivalence failed")
    print(json.dumps({"prefix": args.prefix, "records": len(records), "json": str(json_path.relative_to(ROOT)), "csv": str(csv_path.relative_to(ROOT))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
