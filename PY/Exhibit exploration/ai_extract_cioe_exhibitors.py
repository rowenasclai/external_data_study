#!/usr/bin/env python3
"""Extract the current CIOE 2026 exhibitor list from its public directory API.

Source page:
    https://exhibitors.cioe.cn/gwen/index.html

The page loads records from ``gwen/data/zslist.ashx`` in native 12-row
pages. The extractor follows that public request contract, verifies the final
row count against the endpoint's reported total, and writes UTF-8 CSV/JSON.

Requirements:
    pip install requests beautifulsoup4

Example:
    python ai_extract_cioe_exhibitors.py \
      --output cioe_exhibitors_2026.csv \
      --json-output cioe_exhibitors_2026.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://exhibitors.cioe.cn/gwen/index.html"
API_URL = "https://exhibitors.cioe.cn/gwen/data/zslist.ashx"
RESPONSE_SEPARATOR = "!@#$%^&*"
NATIVE_PAGE_SIZE = 12
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 CIOE-exhibitor-extractor/1.0"
)


def clean_text(value: str) -> str:
    """Collapse source whitespace without changing visible text."""
    return " ".join((value or "").split())


def labelled_values(item: Any) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for dl in item.select("dl"):
        dt = dl.find("dt")
        dd = dl.find("dd")
        if not dt or not dd:
            continue
        label = clean_text(dt.get_text(" ", strip=True)).rstrip("：:").lower()
        values[label] = clean_text(dd.get_text(" ", strip=True))
    return values


def parse_listing_response(payload: str, source_url: str = SOURCE_URL) -> Tuple[List[Dict[str, str]], int]:
    """Parse one CIOE endpoint response into rows and its reported total."""
    if RESPONSE_SEPARATOR not in payload:
        raise ValueError("CIOE response is missing the listing/pagination separator")
    listing_html, pagination_html = payload.split(RESPONSE_SEPARATOR, 1)
    total_match = re.search(r"Total\s*:\s*(\d+)", pagination_html, flags=re.IGNORECASE)
    if not total_match:
        raise ValueError("CIOE response does not report a total record count")
    total = int(total_match.group(1))

    soup = BeautifulSoup(listing_html, "html.parser")
    rows: List[Dict[str, str]] = []
    for item in soup.select("li"):
        link = item.find("a", href=re.compile(r"/jtycn/zsen\d+\.html(?:$|[?#])"))
        title = item.select_one("h3.title")
        if not link or not title:
            continue
        href = str(link.get("href", ""))
        id_match = re.search(r"zsen(\d+)\.html", href)
        if not id_match:
            continue
        labels = labelled_values(item)
        image = item.find("img")
        image_src = str(image.get("src", "")) if image else ""
        rows.append(
            {
                "exhibitor_id": id_match.group(1),
                "company_name": clean_text(title.get_text(" ", strip=True)),
                "exhibition_area": labels.get("exhibition area", ""),
                "hall": labels.get("hall", ""),
                "booth_no": labels.get("booth no", ""),
                "main_products": labels.get("main products", ""),
                "detail_url": urljoin(source_url, href),
                "logo_url": urljoin(source_url, image_src) if image_src else "",
                "source_page": source_url,
            }
        )
    return rows, total


def request_page(
    page_index: int,
    cookies: Dict[str, str],
    timeout: int,
    retries: int,
) -> Tuple[int, List[Dict[str, str]], int]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html, */*; q=0.01",
        "Origin": "https://exhibitors.cioe.cn",
        "Referer": SOURCE_URL,
        "X-Requested-With": "XMLHttpRequest",
    }
    form = {
        "pageindex": str(page_index),
        "pagesize": str(NATIVE_PAGE_SIZE),
        "zq": "",
        "zg": "",
        "zsqy": "",
        "zslx": "",
        "cxtj": "",
        "zpfw": "",
    }
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 2):
        try:
            response = requests.post(
                API_URL,
                params={"method": "dg_zhanshang", "random": str(page_index)},
                data=form,
                headers=headers,
                cookies=cookies,
                timeout=timeout,
            )
            response.raise_for_status()
            rows, total = parse_listing_response(response.text)
            if not rows and total:
                raise ValueError(f"CIOE page {page_index} returned no exhibitor rows")
            return page_index, rows, total
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt <= retries:
                time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"CIOE page {page_index} failed after {retries + 1} attempts: {last_error}")


def validate_rows(rows: Iterable[Dict[str, str]], expected_total: int) -> List[Dict[str, str]]:
    result = list(rows)
    if len(result) != expected_total:
        raise ValueError(f"count mismatch: endpoint reports {expected_total}, extracted {len(result)}")
    ids = [row["exhibitor_id"] for row in result]
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    if duplicate_ids:
        raise ValueError(f"duplicate exhibitor IDs: {', '.join(duplicate_ids[:10])}")
    missing_names = [row["exhibitor_id"] for row in result if not row["company_name"]]
    if missing_names:
        raise ValueError(f"records without company names: {', '.join(missing_names[:10])}")
    return result


def fetch_exhibitors(timeout: int = 60, retries: int = 3, workers: int = 3) -> List[Dict[str, str]]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    landing = session.get(SOURCE_URL, timeout=timeout)
    landing.raise_for_status()
    cookies = session.cookies.get_dict()

    _, first_rows, total = request_page(1, cookies, timeout, retries)
    if total == 0:
        raise ValueError("CIOE endpoint reports zero exhibitors")
    page_count = math.ceil(total / NATIVE_PAGE_SIZE)
    pages: Dict[int, List[Dict[str, str]]] = {1: first_rows}

    if page_count > 1:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {
                executor.submit(request_page, page, cookies, timeout, retries): page
                for page in range(2, page_count + 1)
            }
            completed = 1
            for future in as_completed(futures):
                page_index, page_rows, page_total = future.result()
                if page_total != total:
                    raise ValueError(
                        f"reported total changed during extraction: page 1={total}, "
                        f"page {page_index}={page_total}"
                    )
                pages[page_index] = page_rows
                completed += 1
                if completed % 25 == 0 or completed == page_count:
                    print(f"Fetched {completed}/{page_count} pages", file=sys.stderr)

    ordered: List[Dict[str, str]] = []
    for page_index in range(1, page_count + 1):
        page_rows = pages.get(page_index)
        if page_rows is None:
            raise ValueError(f"missing page {page_index}")
        for row in page_rows:
            row["source_position"] = str(len(ordered) + 1)
            ordered.append(row)
    return validate_rows(ordered, total)


def write_csv(rows: List[Dict[str, str]], path: Path) -> None:
    if not rows:
        raise ValueError("No rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Extract the current CIOE 2026 exhibitor list")
    parser.add_argument("--output", default="cioe_exhibitors_2026.csv", help="CSV output path")
    parser.add_argument("--json-output", default="", help="Optional JSON output path")
    parser.add_argument("--timeout", type=int, default=60, help="Per-request timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Retries per failed page")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent page requests; default 3")
    args = parser.parse_args(argv)
    if args.timeout < 1 or args.retries < 0 or args.workers < 1:
        parser.error("timeout/workers must be positive and retries must be non-negative")

    rows = fetch_exhibitors(timeout=args.timeout, retries=args.retries, workers=args.workers)
    output = Path(args.output)
    write_csv(rows, output)
    if args.json_output:
        write_json(rows, Path(args.json_output))

    print(f"Extracted {len(rows)} CIOE exhibitors")
    print(f"CSV: {output.resolve()}")
    if args.json_output:
        print(f"JSON: {Path(args.json_output).resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
