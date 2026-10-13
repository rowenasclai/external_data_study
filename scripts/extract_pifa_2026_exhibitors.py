#!/usr/bin/env python3
"""Extract PIFA 2026's public server-rendered exhibitor directory."""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

SOURCE_URL = "https://www.prointegrationfuture.asia/2026-exhibitor-list"
USER_AGENT = "external-data-study-pifa-exhibitor-extractor/1.0"
FIELDS = ("exhibitor_id", "company_name", "stand", "profile_url", "source_page", "source_position")


def clean(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_listing(text: str) -> tuple[list[dict[str, str]], int]:
    """Parse complete ordered directory rows and its source-reported total."""
    total_match = re.search(r'data-totalcount="(\d+)"', text)
    if not total_match:
        raise ValueError("PIFA listing does not expose its reported total")
    reported_total = int(total_match.group(1))
    cards = re.findall(
        r'(<article\b[^>]*\bm-exhibitors-list__list__items__item--id-(\d+)[^>]*>.*?</article>)',
        text,
        re.S,
    )
    if reported_total and not cards:
        raise ValueError("PIFA listing has a nonzero total but no exhibitor cards")
    rows: list[dict[str, str]] = []
    for position, (card, exhibitor_id) in enumerate(cards, start=1):
        name_match = re.search(r'<h2\b[^>]*>(.*?)</h2>', card, re.S)
        route_match = re.search(r"openRemoteModal\('([^']+)'", card)
        if not name_match or not route_match:
            raise ValueError(f"PIFA card {exhibitor_id} lacks name or profile route")
        company_name = clean(name_match.group(1))
        route = route_match.group(1).strip()
        if not company_name or not route:
            raise ValueError(f"PIFA card {exhibitor_id} has an empty name or profile route")
        stand_match = re.search(
            r'm-exhibitors-list__list__items__item__header__meta__stand[^>]*>\s*Stand:\s*(.*?)\s*</span>',
            card,
            re.S,
        )
        rows.append(
            {
                "exhibitor_id": exhibitor_id,
                "company_name": company_name,
                "stand": clean(stand_match.group(1)) if stand_match else "",
                "profile_url": urljoin(SOURCE_URL, "/" + route.lstrip("/")),
                "source_page": SOURCE_URL,
                "source_position": str(position),
            }
        )
    return rows, reported_total


def validate(rows: list[dict[str, str]], reported_total: int) -> None:
    if len(rows) != reported_total:
        raise ValueError(f"PIFA count mismatch: extracted {len(rows)}, reported {reported_total}")
    missing = [row["source_position"] for row in rows if not row["company_name"].strip() or not row["profile_url"].startswith("https://")]
    if missing:
        raise ValueError(f"PIFA rows missing required fields at positions {missing[:5]}")
    duplicates = [identifier for identifier, count in Counter(row["exhibitor_id"] for row in rows).items() if count > 1]
    if duplicates:
        raise ValueError(f"PIFA duplicate stable IDs: {duplicates[:5]}")


def fetch() -> str:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            request = Request(SOURCE_URL, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
            with urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise ValueError(f"PIFA unexpected HTTP status {response.status}")
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise RuntimeError(f"PIFA request failed with HTTP {error.code}") from error
            if attempt < 2:
                time.sleep(1 << attempt)
    raise RuntimeError("PIFA request failed after bounded retries") from last_error


def atomic_write(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    for path in (csv_path, json_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8-sig", newline="", dir=csv_path.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        csv_temp = Path(handle.name)
    with NamedTemporaryFile("w", encoding="utf-8", newline="", dir=json_path.parent, delete=False) as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        json_temp = Path(handle.name)
    csv_temp.replace(csv_path)
    json_temp.replace(json_path)


def readback_validate(csv_path: Path, json_path: Path, reported_total: int) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if not csv_rows or list(csv_rows[0]) != list(FIELDS) or csv_rows != json_rows:
        raise ValueError("PIFA CSV/JSON field order or values differ")
    validate(json_rows, reported_total)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()
    rows, total = parse_listing(fetch())
    validate(rows, total)
    atomic_write(rows, args.output, args.json_output)
    readback_validate(args.output, args.json_output, total)
    print(f"records={len(rows)} reported_total={total} csv={args.output} json={args.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
