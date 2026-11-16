#!/usr/bin/env python3
"""Public, deterministic extractor for JMA Hong Kong International Jewelry Show 2026."""
from __future__ import annotations
import argparse
import csv
import html
import json
import re
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE = "https://www.jewelryshows.org/en/trade/exhibitor_directory.php"
UA = "external-data-study-exhibition-crawler/1.0 (+public directory extraction)"
FIELDS = ("exhibitor_id", "company_name", "country_region", "booth", "hall", "product_zone", "telephone", "email", "website", "address", "description", "activity", "products", "brands", "profile_url", "source_position")

def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": UA})
    with urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise ValueError(f"unexpected HTTP status {response.status} for {url}")
        return response.read().decode("utf-8", "strict")

def clean(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return " ".join(value.split())

def parse_listing(page: str) -> list[dict[str, str]]:
    table = re.search(r"<table\b[^>]*>\s*<thead>.*?</thead>\s*<tbody>(.*?)</tbody>", page, re.I | re.S)
    if not table:
        raise ValueError("directory table missing")
    records = []
    for tr in re.finditer(r"<tr\b([^>]*)>(.*?)</tr>", table.group(1), re.I | re.S):
        href = re.search(r'''\bhref=["']([^"']+)["']''', tr.group(1), re.I)
        cells = [clean(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", tr.group(2), re.I | re.S)]
        if len(cells) != 5 or not href:
            raise ValueError("listing row schema drift")
        profile_url = urljoin(BASE, html.unescape(href.group(1)))
        identifier = re.search(r"[?&]id=([^&]+)", profile_url)
        if not identifier or not cells[0]:
            raise ValueError("listing row lacks stable ID or company name")
        records.append(dict(zip(FIELDS[:6], (identifier.group(1), *cells)), profile_url=profile_url))
    if not records:
        raise ValueError("directory listing was empty")
    return records

def parse_profile(page: str) -> dict[str, str]:
    labels = {"Tel.": "telephone", "Email": "email", "Website": "website", "Address": "address", "Introduction": "description", "Activity": "activity", "Exhibits": "products", "Brands": "brands"}
    out = {v: "" for v in labels.values()}
    # Each source field is a complete `div.row`, preventing one value from
    # spilling into the next labelled profile field or organizer footer.
    for label_raw, value_raw in re.findall(r'<div class="row">\s*<div class="name">(.*?)</div>\s*<div class="field">(.*?)</div>\s*</div>', page, re.I | re.S):
        label, value = clean(label_raw), clean(value_raw)
        if label in labels:
            out[labels[label]] = value
    return out

def validate(rows: list[dict[str, str]], expected: int) -> None:
    if len(rows) != expected:
        raise ValueError(f"count mismatch: {len(rows)} != {expected}")
    ids = [r["exhibitor_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate exhibitor IDs")
    for row in rows:
        if not row["company_name"] or not row["profile_url"]:
            raise ValueError("required source field missing")

def atomic_write(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [{field: row.get(field, "") for field in FIELDS} for row in rows]
    with NamedTemporaryFile("w", encoding="utf-8-sig", newline="", dir=csv_path.parent, delete=False) as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader(); writer.writerows(ordered); ctmp = Path(f.name)
    with NamedTemporaryFile("w", encoding="utf-8", dir=json_path.parent, delete=False) as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2); f.write("\n"); jtmp = Path(f.name)
    ctmp.replace(csv_path); jtmp.replace(json_path)

def readback(csv_path: Path, json_path: Path, expected: int) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as f: csv_rows = list(csv.DictReader(f))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if list(csv_rows[0]) != list(FIELDS) or csv_rows != json_rows:
        raise ValueError("CSV/JSON equivalence failure")
    validate(csv_rows, expected)

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--output", type=Path, required=True); ap.add_argument("--json-output", type=Path, required=True); ap.add_argument("--pages", type=int, default=10); args = ap.parse_args()
    pages = []
    for page_number in range(1, args.pages + 1):
        url = BASE if page_number == 1 else f"{BASE}?page={page_number}"
        pages.append(parse_listing(fetch(url)))
        time.sleep(0.25)
    counts = [len(p) for p in pages]
    if len(set(counts[:-1])) != 1 or counts[-1] > counts[0]:
        raise ValueError(f"unexpected native page counts: {counts}")
    rows = []
    for listing in pages:
        rows.extend(listing)
    validate(rows, len(rows))
    for position, row in enumerate(rows, 1):
        row.update(parse_profile(fetch(row["profile_url"])))
        row["source_position"] = str(position)
        time.sleep(0.25)
    validate(rows, len(rows)); atomic_write(rows, args.output, args.json_output); readback(args.output, args.json_output, len(rows))
    print(f"records={len(rows)} pages={args.pages} page_counts={counts} csv={args.output} json={args.json_output}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
