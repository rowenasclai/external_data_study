#!/usr/bin/env python3
"""Extract the public Manufacturing Indonesia 2026 exhibitor directory."""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LANDING_URL = "https://exhibitors.informamarkets-info.com/event/2026MFG/en-US"
API_URL = "https://exhibitors.informamarkets-info.com/api"
PAGE_SIZE = 24
FIELDNAMES = [
    "exhibitor_id",
    "company_name",
    "country",
    "booth",
    "detail_url",
    "source_url",
    "source_position",
]


def request_parameters(start: int) -> dict[str, str]:
    """Return only public parameters used by the directory's own DataTable."""
    return {
        "fn": "getExhibitor",
        "orderfields": '["FeaturedExhibitor","ExhibitorNameEn","StandNoStr","CountryEn"]',
        "filter[country]": "",
        "filter[companyprefix]": "",
        "filter[productcategory]": "",
        "filter[hashtags]": "",
        "filter[businessnature]": "",
        "filter[exhibitortype]": "",
        "filter[venue]": "",
        "filter[fairlocation]": "",
        "HideEmptyProducts": "0",
        "filter[new]": "",
        "filter[sustainable]": "",
        "filter[besustainable]": "",
        "order[0][column]": "0",
        "order[0][dir]": "desc",
        "order[1][column]": "1",
        "order[1][dir]": "asc",
        "start": str(start),
        "length": str(PAGE_SIZE),
        "draw": "1",
        "dt": "1",
        "SearchLog": "1",
        "FairID": "AyITgSTIWLQ5iE7xosD1zQ==",
        "FairCode": "P0bqHr/rxpnLPf/mbui1TQ==",
        "DefineCountry": "False",
        "UseOldCountry": "True",
        "MyList": "0",
        "Email": "",
        "Url": "https://exhibitors.informamarkets-info.com/event/2026MFG",
    }


def fetch_page(start: int, timeout: float) -> dict[str, Any]:
    url = f"{API_URL}?{urlencode(request_parameters(start))}"
    request = Request(
        url,
        headers={
            "User-Agent": "external-data-study-manufacturing-indonesia/1.0",
            "Referer": LANDING_URL,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"page start={start}: HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def slug(name: str) -> str:
    return "".join("-" if ch.isspace() or ch in ",:.&/+%*" else ch.lower() for ch in name).replace("*", "")


def parse_page(payload: dict[str, Any], expected_total: int | None = None) -> tuple[list[dict[str, str]], int]:
    """Pure parser for an API page, with schema and required-field checks."""
    try:
        total = payload["recordsTotal"]
        filtered = payload["recordsFiltered"]
        records = payload["data"]
    except KeyError as exc:
        raise ValueError(f"missing API key: {exc.args[0]}") from exc
    if not isinstance(total, int) or total < 0 or filtered != total:
        raise ValueError("invalid or filtered total")
    if expected_total is not None and total != expected_total:
        raise ValueError(f"inconsistent total: expected {expected_total}, got {total}")
    if not isinstance(records, list) or (total and not records):
        raise ValueError("invalid or unexpectedly empty records")

    rows: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record is not an object")
        exhibitor_id = str(record.get("ExhibitorID", "")).strip()
        company_name = " ".join(str(record.get("ExhibitorNameEn", "")).split())
        if not exhibitor_id or not company_name:
            raise ValueError("record missing stable ID or company name")
        rows.append(
            {
                "exhibitor_id": exhibitor_id,
                "company_name": company_name,
                "country": " ".join(str(record.get("CountryEn", "")).split()),
                "booth": " ".join(str(record.get("StandNoStr", "")).split()),
                "detail_url": f"{LANDING_URL}/exhibitor/{exhibitor_id}/{slug(company_name)}",
                "source_url": LANDING_URL,
                "source_position": "",
            }
        )
    return rows, total


def validate_rows(rows: list[dict[str, str]], total: int, expected_pages: int) -> None:
    if len(rows) != total:
        raise ValueError(f"row count {len(rows)} does not equal total {total}")
    ids = [row["exhibitor_id"] for row in rows]
    if len(set(ids)) != len(ids):
        seen: set[str] = set()
        duplicates: list[str] = []
        for exhibitor_id in ids:
            if exhibitor_id in seen and exhibitor_id not in duplicates:
                duplicates.append(exhibitor_id)
                if len(duplicates) == 10:
                    break
            seen.add(exhibitor_id)
        raise ValueError(f"duplicate stable IDs: {duplicates}")
    if expected_pages != (total + PAGE_SIZE - 1) // PAGE_SIZE:
        raise ValueError("missing or unexpected pages")
    if any(not row["company_name"] or not row["detail_url"].startswith("https://") for row in rows):
        raise ValueError("invalid required output fields")


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def write_outputs(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_bytes(csv_path, buffer.getvalue().encode("utf-8-sig"))
    atomic_write_bytes(json_path, (json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def run(timeout: float, delay: float) -> tuple[list[dict[str, str]], int]:
    first_payload = fetch_page(0, timeout)
    first_rows, total = parse_page(first_payload)
    page_starts = list(range(0, total, PAGE_SIZE))
    pages = {0: first_rows}
    for start in page_starts[1:]:
        if delay:
            time.sleep(delay)
        page_rows, page_total = parse_page(fetch_page(start, timeout), expected_total=total)
        if not page_rows:
            raise ValueError(f"unexpected empty interior page at start={start}")
        pages[start] = page_rows
    if sorted(pages) != page_starts:
        raise ValueError("missing page starts")
    rows = [row for start in page_starts for row in pages[start]]
    for position, row in enumerate(rows, start=1):
        row["source_position"] = str(position)
    validate_rows(rows, total, len(pages))
    return rows, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()
    rows, total = run(args.timeout, args.delay)
    write_outputs(rows, args.output, args.json_output)
    print(f"records={total} csv={args.output} json={args.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
