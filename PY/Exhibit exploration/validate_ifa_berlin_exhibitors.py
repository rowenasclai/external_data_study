#!/usr/bin/env python3
"""Independent quality validator for IFA Berlin exhibitor result artifacts.

Reads the committed CSV and JSON independently, produces a deterministic JSON report,
and exits non-zero if any publishing invariant fails. It never fetches profile pages.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import urlparse

FIELDS = (
    "exhibitor_id", "company_name", "legal_company_name", "country", "show_areas", "halls", "booths",
    "profile_description", "website_url", "detail_url", "logo_url", "source_page", "source_position",
)
IFA_HOST = "www.ifa-berlin.com"
MAX_EXAMPLES = 10
HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, **metrics: Any) -> None:
    checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail, **metrics})


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def values(rows: list[dict[str, str]], field: str) -> list[str]:
    return [row.get(field, "") for row in rows]


def validate(csv_path: Path, json_path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    errors: list[str] = []
    csv_rows: list[dict[str, str]] = []
    json_rows: list[dict[str, Any]] = []

    try:
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            csv_header = tuple(reader.fieldnames or ())
            csv_rows = list(reader)
        add_check(checks, "csv_readable", True, "CSV parsed as UTF-8 with BOM support", rows=len(csv_rows))
        add_check(checks, "csv_field_order", csv_header == FIELDS, "CSV header matches the extraction schema", expected=list(FIELDS), actual=list(csv_header))
        if csv_header != FIELDS:
            errors.append("CSV header/order differs from the extraction schema")
    except (OSError, csv.Error, UnicodeDecodeError) as error:
        add_check(checks, "csv_readable", False, f"Could not parse CSV: {error}")
        errors.append(f"CSV parse failed: {error}")

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise ValueError("JSON root must be a list of objects")
        json_rows = payload
        add_check(checks, "json_readable", True, "JSON parsed as UTF-8 array", rows=len(json_rows))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        add_check(checks, "json_readable", False, f"Could not parse JSON: {error}")
        errors.append(f"JSON parse failed: {error}")

    if errors:
        return {"status": "fail", "csv": str(csv_path), "json": str(json_path), "checks": checks, "warnings": warnings, "errors": errors, "summary": {}}

    json_field_order = tuple(json_rows[0].keys()) if json_rows else ()
    add_check(checks, "json_field_order", json_field_order == FIELDS, "JSON object field order matches the extraction schema", expected=list(FIELDS), actual=list(json_field_order))
    if json_field_order != FIELDS:
        errors.append("JSON field order differs from the extraction schema")

    equivalent = csv_rows == json_rows
    add_check(checks, "csv_json_equivalence", equivalent, "CSV and JSON are field-for-field equivalent", csv_rows=len(csv_rows), json_rows=len(json_rows))
    if not equivalent:
        errors.append("CSV and JSON contents differ")

    ids = values(csv_rows, "exhibitor_id")
    missing_ids = [index + 1 for index, value in enumerate(ids) if not value.strip()]
    duplicate_ids = sorted(identifier for identifier, count in Counter(ids).items() if identifier and count > 1)
    add_check(checks, "stable_ids", not missing_ids and not duplicate_ids, "Every row has one unique published exhibitor ID", missing_rows=missing_ids[:MAX_EXAMPLES], duplicate_ids=duplicate_ids[:MAX_EXAMPLES])
    if missing_ids:
        errors.append("Missing exhibitor IDs")
    if duplicate_ids:
        errors.append("Duplicate exhibitor IDs")

    company_names = values(csv_rows, "company_name")
    missing_companies = [index + 1 for index, value in enumerate(company_names) if not value.strip()]
    add_check(checks, "company_names", not missing_companies, "Every row has a display company name", missing_rows=missing_companies[:MAX_EXAMPLES])
    if missing_companies:
        errors.append("Missing company names")

    positions = values(csv_rows, "source_position")
    expected_positions = [str(index) for index in range(1, len(csv_rows) + 1)]
    add_check(checks, "source_position_sequence", positions == expected_positions, "Source positions are sequential and deterministic", rows=len(csv_rows))
    if positions != expected_positions:
        errors.append("Source positions are not a 1-based sequence")

    bad_detail_urls = [row["exhibitor_id"] for row in csv_rows if row["detail_url"] and (not is_http_url(row["detail_url"]) or urlparse(row["detail_url"]).netloc != IFA_HOST or not urlparse(row["detail_url"]).path.startswith("/exhibitors/"))]
    add_check(checks, "detail_profile_urls", not bad_detail_urls, "Non-empty exhibitor profile URLs are canonical IFA HTTPS/HTTP URLs", invalid_ids=bad_detail_urls[:MAX_EXAMPLES])
    if bad_detail_urls:
        errors.append("Invalid IFA exhibitor profile URLs")

    bad_source_urls = [row["exhibitor_id"] for row in csv_rows if not is_http_url(row["source_page"]) or urlparse(row["source_page"]).netloc != IFA_HOST]
    add_check(checks, "source_urls", not bad_source_urls, "Every row retains a canonical IFA source-page URL", invalid_ids=bad_source_urls[:MAX_EXAMPLES])
    if bad_source_urls:
        errors.append("Invalid source-page URLs")

    for field in ("website_url", "logo_url"):
        invalid = [row["exhibitor_id"] for row in csv_rows if row[field] and not is_http_url(row[field])]
        add_check(checks, f"{field}_syntax", not invalid, f"Non-empty {field} values are absolute HTTP(S) URLs", invalid_ids=invalid[:MAX_EXAMPLES])
        if invalid:
            errors.append(f"Invalid {field} values")

    html_descriptions = [row["exhibitor_id"] for row in csv_rows if HTML_TAG_RE.search(row["profile_description"])]
    add_check(checks, "description_plain_text", not html_descriptions, "Profile descriptions contain normalized text rather than HTML markup", invalid_ids=html_descriptions[:MAX_EXAMPLES])
    if html_descriptions:
        errors.append("Profile descriptions contain HTML markup")

    for field, label in (("legal_company_name", "legal company names"), ("profile_description", "profile descriptions"), ("website_url", "website URLs"), ("detail_url", "profile URLs")):
        present = sum(bool(row[field].strip()) for row in csv_rows)
        missing = len(csv_rows) - present
        warnings.append({"field": field, "label": label, "present": present, "blank": missing, "message": "Blank values are preserved where the public IFA profile did not publish the field."})

    summary = {
        "records": len(csv_rows),
        "unique_exhibitor_ids": len(set(ids)),
        "legal_company_names_present": sum(bool(row["legal_company_name"].strip()) for row in csv_rows),
        "profile_descriptions_present": sum(bool(row["profile_description"].strip()) for row in csv_rows),
        "website_urls_present": sum(bool(row["website_url"].strip()) for row in csv_rows),
        "profile_urls_present": sum(bool(row["detail_url"].strip()) for row in csv_rows),
    }
    return {"status": "pass" if not errors else "fail", "csv": str(csv_path), "json": str(json_path), "checks": checks, "warnings": warnings, "errors": errors, "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate IFA Berlin exhibitor CSV/JSON artifacts")
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.csv, args.json)
    atomic_json_write(args.report, report)
    print(json.dumps({"status": report["status"], "report": str(args.report), "summary": report["summary"]}, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
