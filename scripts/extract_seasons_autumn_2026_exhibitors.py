#!/usr/bin/env python3
"""Extract the public SEASONS | Autumn 2026 exhibitor directory.

The organizer's public directory serves the complete current edition listing
through the same GET /api request used by its visible DataTables UI.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LANDING_URL = "https://exhibitors.informamarkets-info.com/event/20269FJ/en-US"
API_URL = "https://exhibitors.informamarkets-info.com/api"
FIELDS = [
    "exhibitor_id", "company_name", "booth", "country", "exhibitor_type",
    "business_nature", "product_categories", "description", "website", "brands",
    "detail_page_url", "source_scope", "source_position", "source_url",
]


def api_parameters() -> dict[str, str | int]:
    # The page's own DataTables configuration requests its native complete list
    # with length=10000; the response's recordsTotal is still enforced below.
    return {
        "fn": "getExhibitor",
        "orderfields": '["FeaturedExhibitor","ExhibitorNameEn","StandNoStr","CountryEn"]',
        "start": 0, "length": 10000, "draw": 1, "dt": 1, "SearchLog": 1,
        "FairID": "UQMPpB5vYgY5HrfYaP4EcA==", "FairCode": "1mc52kp88nzSDez2cLllig==",
        "DefineCountry": "False", "UseOldCountry": "False", "MyList": 0,
        "Email": "", "Url": LANDING_URL,
    }


def fetch_payload() -> dict:
    request = Request(
        f"{API_URL}?{urlencode(api_parameters())}",
        headers={"User-Agent": "external-data-study/1.0 (+public-directory-validation)"},
    )
    with urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise ValueError(f"unexpected HTTP status {response.status}")
        return json.loads(response.read().decode("utf-8"))


def normalized_categories(value: object) -> str:
    """The source emits an unordered category set; stabilize its serialization."""
    return ",".join(sorted(part.strip() for part in str(value or "").split(",") if part.strip()))


def detail_url(record: dict) -> str:
    identifier = str(record.get("ExhibitorID", "")).strip()
    friendly = str(record.get("FriendlyUrl", "")).strip().strip("/")
    if not identifier:
        return ""
    suffix = f"/{friendly}" if friendly else ""
    return f"{LANDING_URL}/exhibitor/{identifier}{suffix}"


def parse_payload(payload: dict) -> tuple[list[dict[str, str]], int]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("payload lacks data list")
    try:
        total = int(payload["recordsTotal"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("payload lacks integer recordsTotal") from error
    rows = []
    for index, record in enumerate(payload["data"], start=1):
        identifier = str(record.get("ExhibitorID", "")).strip()
        name = str(record.get("ExhibitorNameEn") or record.get("ExhibitorNameCht") or record.get("ExhibitorNameChs") or "").strip()
        rows.append({
            "exhibitor_id": identifier,
            "company_name": name,
            "booth": str(record.get("StandNoStr", "")).strip(),
            "country": str(record.get("CountryEn") or record.get("Country", "")).strip(),
            "exhibitor_type": str(record.get("ExhibitorTypeEn", "")).strip(),
            "business_nature": str(record.get("BusinessNatureEn", "")).strip(),
            "product_categories": normalized_categories(record.get("ProductCategoryEn", "")),
            "description": str(record.get("DescEn", "")).strip(),
            "website": str(record.get("LinkEn", "")).strip(),
            "brands": str(record.get("BrandEn", "")).strip(),
            "detail_page_url": detail_url(record),
            "source_scope": "All exhibitors",
            "source_position": str(index),
            "source_url": LANDING_URL,
        })
    return rows, total


def validate(rows: list[dict[str, str]], total: int) -> None:
    if total < 0 or len(rows) != total:
        raise ValueError(f"count mismatch: rows={len(rows)} reported_total={total}")
    missing_names = [row["source_position"] for row in rows if not row["company_name"]]
    if missing_names:
        raise ValueError(f"missing company names at positions {missing_names[:8]}")
    identifiers = [row["exhibitor_id"] for row in rows]
    duplicate_ids = [key for key, count in Counter(identifiers).items() if not key or count > 1]
    if duplicate_ids:
        raise ValueError(f"missing or duplicate IDs: {duplicate_ids[:8]}")
    if any(not row["detail_page_url"].startswith("https://") for row in rows):
        raise ValueError("non-HTTPS or missing detail URL")


def atomic_write(path: Path, text: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def write_outputs(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    from io import StringIO
    csv_buffer = StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(csv_path, csv_buffer.getvalue(), "utf-8-sig")
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")


def read_back(csv_path: Path, json_path: Path, total: int) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError("CSV field order mismatch")
        csv_rows = [{field: row.get(field, "") for field in FIELDS} for row in reader]
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if csv_rows != json_rows:
        raise ValueError("CSV/JSON read-back mismatch")
    validate(csv_rows, total)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()
    rows, total = parse_payload(fetch_payload())
    validate(rows, total)
    write_outputs(rows, args.output, args.json_output)
    read_back(args.output, args.json_output, total)
    print(f"validated rows={len(rows)} reported_total={total} csv={args.output} json={args.json_output}")


if __name__ == "__main__":
    main()
