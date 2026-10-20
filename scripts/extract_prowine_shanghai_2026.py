#!/usr/bin/env python3
"""Extract the public ProWine Shanghai 2026 exhibitor listing.

The server-rendered directory has 10 records per native page.  It has no
record ID, so the documented identity is the source-published compound key
(country, booth number, company name); all 64 pages must equal the country
counts exposed by the first listing page.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import tempfile
import time
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LISTING_URL = "https://www.prowine-shanghai.com/en/exhibition"
PAGE_SIZE = 10
FIELDS = ["exhibitor_key", "company_name", "booth_no", "country", "profile_url", "source_url", "source_position"]
USER_AGENT = "external-data-study-prowine-shanghai-extractor/1.0"


def text(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def fetch_page(page: int, *, timeout: int = 30, retries: int = 2) -> str:
    url = LISTING_URL if page == 1 else f"{LISTING_URL}?expo_id=8&page={page}"
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=timeout) as response:
                if response.status != 200: raise ValueError(f"page {page}: HTTP {response.status}")
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            transient = not isinstance(exc, HTTPError) or exc.code in {408, 429, 500, 502, 503, 504}
            if not transient or attempt == retries: raise RuntimeError(f"page {page}, attempt={attempt + 1}: request failed") from exc
            time.sleep(min(4, 2 ** attempt))
    raise AssertionError("unreachable")


def parse_page(document: str) -> list[dict[str, str]]:
    cards = re.findall(r'<li\s+class="DemoonstrationList"[^>]*>(.*?)</li>', document, re.I | re.S)
    if not cards: raise ValueError("listing page has no exhibitor cards")
    rows = []
    for card in cards:
        name_match = re.search(r'<strong\s+class="DemoonstrationList-name"[^>]*>(.*?)</strong>', card, re.I | re.S)
        country_match = re.search(r'DemoonstrationList-Country"[^>]*>\s*Country：\s*(.*?)</span>', card, re.I | re.S)
        booth_match = re.search(r'DemoonstrationList-Booth"[^>]*>\s*Booth No\.：\s*(.*?)</span>', card, re.I | re.S)
        if not (name_match and country_match and booth_match): raise ValueError("listing card lacks required name/country/booth")
        name, country, booth = (text(match.group(1)) for match in (name_match, country_match, booth_match))
        if not name: raise ValueError("listing card has blank company name")
        rows.append({"exhibitor_key": f"{country}|{booth}|{name}", "company_name": name, "booth_no": booth,
                     "country": country, "profile_url": "", "source_url": LISTING_URL, "source_position": ""})
    return rows


def metadata(document: str) -> tuple[int, int]:
    counts = [int(value) for value in re.findall(r'<option\s+value="[^"]+"[^>]*>[^<(]*\((\d+)\)', document, re.I)]
    pages = [int(value) for value in re.findall(r'[?&]page=(\d+)', html.unescape(document), re.I)]
    total, last_page = sum(counts), max(pages, default=1)
    if not total or last_page < 1: raise ValueError("listing lacks country-count total or pagination")
    return total, last_page


def validate(rows: list[dict[str, str]], total: int, pages: list[int], last_page: int) -> None:
    if pages != list(range(1, last_page + 1)) or len(rows) != total:
        raise ValueError(f"incomplete pagination: rows={len(rows)} total={total} pages={pages}")
    keys = [row["exhibitor_key"] for row in rows]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates: raise ValueError(f"duplicate compound keys: {duplicates[:5]}")
    if any(not row["company_name"] for row in rows): raise ValueError("blank company name")


def write_artifacts(rows: list[dict[str, str]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "prowine_shanghai_2026_exhibitors.csv"
    json_path = output_dir / "prowine_shanghai_2026_exhibitors.json"
    for position, row in enumerate(rows, 1): row["source_position"] = str(position)
    for path, kind in ((csv_path, "csv"), (json_path, "json")):
        fd, temporary_name = tempfile.mkstemp(dir=output_dir, prefix=f".{path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig" if kind == "csv" else "utf-8", newline="") as handle:
                if kind == "csv":
                    writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
                else: json.dump(rows, handle, ensure_ascii=False, indent=2); handle.write("\n")
                handle.flush(); os.fsync(handle.fileno())
            Path(temporary_name).replace(path)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True); raise
    return csv_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("Result/Other Events/ProWine Shanghai 2026"))
    args = parser.parse_args()
    first = fetch_page(1); total, last_page = metadata(first)
    pages: dict[int, list[dict[str, str]]] = {1: parse_page(first)}
    for page in range(2, last_page + 1):
        rows = parse_page(fetch_page(page))
        if page < last_page and not rows: raise ValueError(f"empty interior page {page}")
        pages[page] = rows
    ordered = [row for page in sorted(pages) for row in pages[page]]
    validate(ordered, total, sorted(pages), last_page)
    csv_path, json_path = write_artifacts(ordered, args.output_dir)
    print(json.dumps({"records": total, "csv": str(csv_path), "json": str(json_path)}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
