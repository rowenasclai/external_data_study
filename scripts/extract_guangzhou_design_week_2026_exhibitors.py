#!/usr/bin/env python3
"""Extract the public Guangzhou Design Week exhibitor directory.

The official visible Exhibitors page loads https://enapi.gzdesignweek.com/exhibitors.
Its listing items expose company name, category, venue, stand, logo, and stable code;
no individual profile hyperlink or profile fields are published in the listing.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://enapi.gzdesignweek.com/exhibitors"
LANDING_URL = "https://en.gzdesignweek.com/exhibitors"
USER_AGENT = "external-data-study-gzdesignweek-directory/1.0"
FIELDS = (
    "exhibitor_id", "company_name", "profile_url", "profile_status", "category",
    "venue", "stand", "logo_url", "source_url", "source_position",
)
# Totals shown in the official visible UI at extraction time. A change requires
# rechecking the live directory rather than silently accepting partial coverage.
EXPECTED_CATEGORY_COUNTS = {
    "Soft Furnishing + Home Deco": 142,
    "Integrated/Customized Furniture + Decorative Materials": 313,
    "Technical Skill + Lifestyle": 73,
}


def fetch() -> dict:
    request = Request(API_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(2):
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"unexpected HTTP status {response.status}")
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("API response is not a JSON object")
                return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            retryable = isinstance(exc, (URLError, TimeoutError)) or (
                isinstance(exc, HTTPError) and (exc.code in (408, 429) or exc.code >= 500)
            )
            if not retryable or attempt:
                raise RuntimeError(f"directory request failed ({type(exc).__name__})") from exc
            time.sleep(2)
    raise RuntimeError("directory request failed after bounded retry")


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def parse_payload(payload: dict, expected_counts: dict[str, int] | None = EXPECTED_CATEGORY_COUNTS) -> list[dict[str, str]]:
    groups = payload.get("data")
    if not isinstance(groups, list) or not groups:
        raise ValueError("API response has no category list")
    rows: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("category entry is not an object")
        category = text(group.get("category"))
        venue = text(group.get("venue"))
        children = group.get("children")
        if not category or not isinstance(children, list):
            raise ValueError("category is missing its name or exhibitor list")
        for item in children:
            if not isinstance(item, dict):
                raise ValueError(f"invalid exhibitor entry in category {category!r}")
            code = text(item.get("code"))
            name = " ".join(text(item.get("company_name")).split())
            item_category = text(item.get("category"))
            item_venue = text(item.get("venue")) or venue
            logo_url = text(item.get("logo"))
            if not code or not name:
                raise ValueError(f"exhibitor in {category!r} lacks stable code or name")
            if item_category != category:
                raise ValueError(f"exhibitor category mismatch for {code}")
            rows.append({
                "exhibitor_id": code,
                "company_name": name,
                "profile_url": "",
                "profile_status": "not_linked_on_source",
                "category": category,
                "venue": item_venue,
                "stand": text(item.get("stand_code")),
                "logo_url": logo_url,
                "source_url": API_URL,
                "source_position": str(len(rows) + 1),
            })
            counts[category] += 1
    if expected_counts is not None and dict(counts) != expected_counts:
        raise ValueError(f"UI/API category totals changed or disagree: {dict(counts)!r}")
    validate(rows, expected_counts)
    return rows


def validate(rows: list[dict[str, str]], expected_counts: dict[str, int] | None = EXPECTED_CATEGORY_COUNTS) -> None:
    if expected_counts is not None and len(rows) != sum(expected_counts.values()):
        raise ValueError("total record count does not match the official category totals")
    if any(tuple(row) != FIELDS for row in rows):
        raise ValueError("row field order or schema is invalid")
    ids = [row["exhibitor_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate stable exhibitor IDs")
    if any(not row["company_name"] or not row["source_url"].startswith("https://") for row in rows):
        raise ValueError("required name or source URL is blank/invalid")
    if any(row["profile_url"] or row["profile_status"] != "not_linked_on_source" for row in rows):
        raise ValueError("profile links must remain blank when none are published")


def atomic_write(path: Path, content: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def write_outputs(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    import io
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=list(FIELDS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(csv_path, csv_buffer.getvalue(), "utf-8-sig")
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if csv_rows != json_rows or len(csv_rows) != len(rows):
        raise ValueError("CSV/JSON read-back equivalence failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("Result/Other Events/Guangzhou Design Week 2026/guangzhou_design_week_2026_exhibitors.csv"))
    parser.add_argument("--json-output", type=Path, default=Path("Result/Other Events/Guangzhou Design Week 2026/guangzhou_design_week_2026_exhibitors.json"))
    args = parser.parse_args()
    rows = parse_payload(fetch())
    write_outputs(rows, args.output, args.json_output)
    print(json.dumps({
        "event_url": LANDING_URL,
        "source_url": API_URL,
        "records": len(rows),
        "category_counts": dict(Counter(row["category"] for row in rows)),
        "unique_ids": len({row["exhibitor_id"] for row in rows}),
        "profile_urls": sum(bool(row["profile_url"]) for row in rows),
        "csv": str(args.output),
        "json": str(args.json_output),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
