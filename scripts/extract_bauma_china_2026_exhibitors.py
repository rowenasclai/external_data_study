#!/usr/bin/env python3
"""Extract the public bauma CHINA 2026 exhibitor directory.

The official server-rendered directory exposes 24 native records per page and
page links through its terminal page.  No authentication or browser state is
used.  CSV and JSON are derived from one validated ordered record list.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://community.b-china.cn/en/exhibitions?ctype=0&hall=0&page={page}"
DETAIL_BASE = "https://community.b-china.cn"
USER_AGENT = "external-data-study-bauma-china-directory/1.0"
FIELDS = ("exhibitor_id", "company_name", "country_region", "booth", "detail_url", "source_url", "source_position")


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value))).strip()


def parse_page(text: str, source_url: str) -> tuple[list[dict[str, str]], int]:
    """Parse one server-rendered listing page without network access."""
    body = re.search(r"<tbody\b[^>]*>(.*?)</tbody\s*>", text, re.I | re.S)
    if not body:
        raise ValueError("directory response has no table body")
    rows: list[dict[str, str]] = []
    for fragment in re.findall(r"<tr\b[^>]*>(.*?)</tr\s*>", body.group(1), re.I | re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td\s*>", fragment, re.I | re.S)
        if len(cells) != 4:
            raise ValueError(f"expected four listing cells, found {len(cells)}")
        match = re.search(r'href=["\'](/en/exhibition/info/(\d+))["\']', cells[0], re.I)
        if not match:
            raise ValueError("listing row lacks immutable exhibitor detail ID")
        name = normalise(cells[0])
        if not name:
            raise ValueError(f"listing row {match.group(2)} lacks company name")
        rows.append({
            "exhibitor_id": match.group(2),
            "company_name": name,
            "country_region": normalise(cells[2]),
            "booth": normalise(cells[1]),
            "detail_url": DETAIL_BASE + match.group(1),
            "source_url": source_url,
        })
    if not rows:
        raise ValueError("directory page contains zero rows")
    pages = [int(number) for number in re.findall(r"(?:[?&]|&amp;)page=(\d+)", text)]
    if not pages:
        raise ValueError("directory response has no pagination links")
    return rows, max(pages)


def fetch(page: int, retries: int, delay: float) -> tuple[str, str]:
    url = BASE_URL.format(page=page)
    for attempt in range(1, retries + 2):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise RuntimeError(f"page {page}: unexpected HTTP {response.status}")
                return response.read().decode("utf-8"), response.url
        except (HTTPError, URLError, TimeoutError) as exc:
            transient = isinstance(exc, URLError) or (isinstance(exc, HTTPError) and (exc.code == 408 or exc.code == 429 or exc.code >= 500))
            if not transient or attempt > retries:
                raise RuntimeError(f"page {page} attempt {attempt} failed: {type(exc).__name__}") from exc
            time.sleep(min(8.0, delay * (2 ** (attempt - 1))))


def validate(rows: list[dict[str, str]], expected_pages: int, fetched_pages: list[int]) -> None:
    if fetched_pages != list(range(1, expected_pages + 1)):
        raise ValueError("missing or out-of-order native pages")
    ids = [row["exhibitor_id"] for row in rows]
    duplicates = [key for key, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate immutable exhibitor IDs: {duplicates[:10]}")
    for row in rows:
        if not row["company_name"]:
            raise ValueError("blank company name")
        if not row["detail_url"].startswith(DETAIL_BASE + "/en/exhibition/info/"):
            raise ValueError("unexpected detail URL")


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
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(csv_path, csv_buffer.getvalue(), "utf-8-sig")
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")


def readback_validate(csv_path: Path, json_path: Path, expected_count: int) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
        if tuple(handle.seek(0) or next(csv.reader(handle))) != FIELDS:
            raise ValueError("CSV field order changed")
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if len(csv_rows) != expected_count or len(json_rows) != expected_count:
        raise ValueError("artifact count mismatch")
    if [[row[field] for field in FIELDS] for row in csv_rows] != [[str(row[field]) for field in FIELDS] for row in json_rows]:
        raise ValueError("CSV and JSON are not field-for-field equivalent")
    validate(csv_rows, expected_pages=1, fetched_pages=[1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()

    first_text, first_final_url = fetch(1, args.retries, args.delay)
    first_rows, pages = parse_page(first_text, first_final_url)
    all_rows = list(first_rows)
    fetched_pages = [1]
    for page in range(2, pages + 1):
        time.sleep(args.delay)
        text, final_url = fetch(page, args.retries, args.delay)
        page_rows, page_count = parse_page(text, final_url)
        if page_count != pages:
            raise ValueError(f"page {page} pagination changed from {pages} to {page_count}")
        all_rows.extend(page_rows)
        fetched_pages.append(page)
    for position, row in enumerate(all_rows, start=1):
        row["source_position"] = str(position)
    validate(all_rows, pages, fetched_pages)
    write_outputs(all_rows, args.output, args.json_output)
    readback_validate(args.output, args.json_output, len(all_rows))
    print(f"pages={pages} records={len(all_rows)} csv={args.output} json={args.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
