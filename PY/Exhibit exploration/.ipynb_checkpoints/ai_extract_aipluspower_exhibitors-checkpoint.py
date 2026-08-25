#!/usr/bin/env python3
"""
Extract the exhibitor list from AI+ Power's Wix exhibitor page.

Source page:
    https://www.aipluspower.com/exhibitor-list

The exhibitor records are embedded in the page HTML inside the Wix warmup JSON:
    <script type="application/json" id="wix-warmup-data">...</script>

No browser automation is required.

Requirements:
    pip install requests

Examples:
    python extract_aipluspower_exhibitors.py
    python extract_aipluspower_exhibitors.py --output exhibitors.csv
    python extract_aipluspower_exhibitors.py --json-output exhibitors.json
    python extract_aipluspower_exhibitors.py --url https://www.aipluspower.com/exhibitor-list
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

DEFAULT_URL = "https://www.aipluspower.com/exhibitor-list"
DEFAULT_COLLECTION_ID = "2026ExhibitorList"


def fetch_html(url: str, timeout: int = 60) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_wix_warmup_data(page_html: str) -> Dict[str, Any]:
    match = re.search(
        r'<script[^>]+id=["\']wix-warmup-data["\'][^>]*>(.*?)</script>',
        page_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not match:
        raise ValueError("Could not find <script id='wix-warmup-data'> in page HTML")

    # Wix stores JSON directly in the script tag. html.unescape is safe here and
    # handles entities if Wix emits any.
    raw_json = html.unescape(match.group(1).strip())
    return json.loads(raw_json)


def get_nested(data: Dict[str, Any], path: Iterable[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def find_records_by_collection_id(data: Dict[str, Any], collection_id: str) -> Dict[str, Dict[str, Any]]:
    records = get_nested(
        data,
        [
            "appsWarmupData",
            "dataBinding",
            "dataStore",
            "recordsByCollectionId",
            collection_id,
        ],
    )
    if isinstance(records, dict):
        return records

    available = get_nested(
        data,
        ["appsWarmupData", "dataBinding", "dataStore", "recordsByCollectionId"],
    )
    if isinstance(available, dict):
        raise ValueError(
            f"Collection {collection_id!r} not found. Available collections: "
            + ", ".join(sorted(available.keys()))
        )
    raise ValueError("Could not find Wix recordsByCollectionId data")


def date_value(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("$date", ""))
    return str(value or "")


def list_value(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if v is not None)
    return str(value or "")


def normalize_records(records: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for record_id, record in records.items():
        rows.append(
            {
                "ref_no": record.get("refNo", ""),
                "company_name_en": record.get("companyNameEn", ""),
                "company_name_cn": record.get("companyNameCn", ""),
                "booth_no": record.get("boothNo", ""),
                "website": record.get("website", ""),
                "main_scope_of_business": list_value(record.get("mainScopeOfBusiness"))
                or str(record.get("mainScopeOfBusiness1", "")),
                "record_id": record.get("_id", record_id),
                "image_wix_url": record.get("image", ""),
                "logo": record.get("logo", ""),
                "created_date": date_value(record.get("_createdDate")),
                "updated_date": date_value(record.get("_updatedDate")),
            }
        )

    def sort_key(row: Dict[str, Any]) -> tuple:
        ref = row.get("ref_no", "")
        try:
            ref_sort = int(ref)
        except (TypeError, ValueError):
            ref_sort = 999_999
        return (ref_sort, str(row.get("company_name_en", "")))

    rows.sort(key=sort_key)
    return rows


def write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        raise ValueError("No rows to write")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: List[Dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def extract_exhibitors(url: str, collection_id: str) -> List[Dict[str, Any]]:
    page_html = fetch_html(url)
    warmup_data = extract_wix_warmup_data(page_html)
    records = find_records_by_collection_id(warmup_data, collection_id)
    return normalize_records(records)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Extract AI+ Power exhibitor list from Wix warmup data")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Source URL, default: {DEFAULT_URL}")
    parser.add_argument(
        "--collection-id",
        default=DEFAULT_COLLECTION_ID,
        help=f"Wix collection ID, default: {DEFAULT_COLLECTION_ID}",
    )
    parser.add_argument("--output", default="aipluspower_exhibitors_2026.csv", help="CSV output path")
    parser.add_argument("--json-output", default="", help="Optional JSON output path")
    args = parser.parse_args(argv)

    rows = extract_exhibitors(args.url, args.collection_id)
    write_csv(rows, Path(args.output))
    if args.json_output:
        write_json(rows, Path(args.json_output))

    print(f"Extracted {len(rows)} exhibitors")
    print(f"CSV: {Path(args.output).resolve()}")
    if args.json_output:
        print(f"JSON: {Path(args.json_output).resolve()}")
    if rows:
        first = rows[0]
        print(
            "First record: "
            f"{first.get('company_name_en', '')} | "
            f"{first.get('company_name_cn', '')} | "
            f"{first.get('booth_no', '')}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
