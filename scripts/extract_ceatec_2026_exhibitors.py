#!/usr/bin/env python3
"""Extract CEATEC 2026's public server-rendered exhibitor directory.

The official English list embeds all parent exhibitors and their named
co-exhibitors in one unauthenticated HTML response (``per=all``).  Parent
records have source-published numeric IDs; the page gives co-exhibitors no
separate IDs, so their deterministic identity is the documented compound
``parent:<id>:co-exhibitor:<ordinal>``.
"""
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
from urllib.request import Request, urlopen

SOURCE_URL = "https://www.ceatec.com/en/exhibition/exhibitor-list.php"
USER_AGENT = "external-data-study-ceatec-exhibitor-extractor/1.0"
FIELDS = (
    "exhibitor_id", "company_name", "exhibitor_type", "parent_exhibitor_id",
    "area", "hall", "booth", "detail_url", "source_page", "source_position",
)


def clean(fragment: str) -> str:
    value = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(value).split()).lstrip("●").strip()


def parse_listing(text: str) -> tuple[list[dict[str, str]], int, int]:
    """Return ordered parent/co-exhibitor rows, source total, and parent count."""
    total_match = re.search(r'exl-header__total-num">\s*(\d+)\s*<', text)
    if not total_match:
        raise ValueError("CEATEC listing does not expose its reported total")
    reported_total = int(total_match.group(1))
    cards = re.findall(r"(<article\b[^>]*\bdata-exl-card\b.*?</article>)", text, re.S)
    if not cards:
        raise ValueError("CEATEC listing contains no exhibitor cards")
    rows: list[dict[str, str]] = []
    for card in cards:
        identifier = re.search(r'\bdata-id="([^"]+)"', card)
        name = re.search(r'<h3 class="exl-card__name">(.*?)</h3>', card, re.S)
        if not identifier or not name:
            raise ValueError("CEATEC exhibitor card lacks source ID or name")
        parent_id = identifier.group(1).strip()
        company_name = clean(name.group(1))
        if not parent_id or not company_name:
            raise ValueError("CEATEC exhibitor card has empty source ID or name")
        def field(class_name: str) -> str:
            found = re.search(rf'<span class="{class_name}"[^>]*>(.*?)</span>', card, re.S)
            return clean(found.group(1)) if found else ""
        parent = {
            "exhibitor_id": f"parent:{parent_id}", "company_name": company_name,
            "exhibitor_type": "parent", "parent_exhibitor_id": "", "area": field("exl-card__area"),
            "hall": field("exl-card__hall"), "booth": field("exl-card__booth"), "detail_url": "",
            "source_page": SOURCE_URL,
        }
        rows.append(parent)
        # Each card has both full and compact renderings.  Co-exhibitor buttons
        # appear in both, so parse the authoritative full rendering only.
        full_card = card.split("<!-- ========== Compact view ========== -->", 1)[0]
        children = re.findall(r'<button[^>]*class="[^"]*\bexl-child\b[^"]*"[^>]*>(.*?)</button>', full_card, re.S)
        for ordinal, child in enumerate(children, start=1):
            child_name = clean(child)
            if not child_name:
                raise ValueError(f"CEATEC co-exhibitor {parent_id}:{ordinal} has no name")
            rows.append({
                "exhibitor_id": f"parent:{parent_id}:co-exhibitor:{ordinal}", "company_name": child_name,
                "exhibitor_type": "co_exhibitor", "parent_exhibitor_id": parent_id,
                "area": parent["area"], "hall": parent["hall"], "booth": parent["booth"],
                "detail_url": "", "source_page": SOURCE_URL,
            })
    for position, row in enumerate(rows, start=1):
        row["source_position"] = str(position)
    return rows, reported_total, len(cards)


def validate(rows: list[dict[str, str]], reported_total: int) -> None:
    if len(rows) != reported_total:
        raise ValueError(f"CEATEC count mismatch: extracted {len(rows)}, reported {reported_total}")
    missing = [row["source_position"] for row in rows if not row["company_name"].strip() or not row["source_page"].startswith("https://")]
    if missing:
        raise ValueError(f"CEATEC rows missing required fields at positions {missing[:5]}")
    ids = [row["exhibitor_id"] for row in rows]
    duplicates = sorted(identifier for identifier, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"CEATEC duplicate stable IDs: {duplicates[:5]}")


def fetch() -> str:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            request = Request(SOURCE_URL, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
            with urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise ValueError(f"CEATEC unexpected HTTP status {response.status}")
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise RuntimeError(f"CEATEC request failed with HTTP {error.code}") from error
            if attempt < 2:
                time.sleep(1 << attempt)
    raise RuntimeError("CEATEC request failed after bounded retries") from last_error


def atomic_write(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    for path in (csv_path, json_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8-sig", newline="", dir=csv_path.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
        csv_temp = Path(handle.name)
    with NamedTemporaryFile("w", encoding="utf-8", newline="", dir=json_path.parent, delete=False) as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2); handle.write("\n")
        json_temp = Path(handle.name)
    csv_temp.replace(csv_path); json_temp.replace(json_path)


def readback_validate(csv_path: Path, json_path: Path, reported_total: int) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if list(csv_rows[0]) != list(FIELDS) or csv_rows != json_rows:
        raise ValueError("CEATEC CSV/JSON field order or values differ")
    validate(json_rows, reported_total)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()
    rows, total, parents = parse_listing(fetch())
    validate(rows, total)
    atomic_write(rows, args.output, args.json_output)
    readback_validate(args.output, args.json_output, total)
    print(f"records={len(rows)} reported_total={total} parent_cards={parents} csv={args.output} json={args.json_output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
