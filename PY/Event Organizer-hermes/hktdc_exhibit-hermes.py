#!/usr/bin/env python3
"""Extract a public HKTDC exhibitor directory from SSR Next.js data.

No login, cookies, or browser automation are required. Results are written only
beneath Result/Exhibition Organizers/HKTDC-hermes/.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "Result" / "Exhibition Organizers" / "HKTDC-hermes"
PAGE_SIZE = 50
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
FIELDS = (
    "id", "exhibitor_name", "country", "booth_numbers", "exhibitor_urn",
    "supplier_urn", "virtual_booth_url", "contact_url", "source_position", "source_url",
)


def source_url(prefix: str, page_num: int, page_size: int) -> str:
    return "https://www.hktdc.com/event/{}/en/exhibitor-list?{}".format(
        prefix, urlencode({"pageNum": page_num, "pageSize": page_size})
    )


def fetch_page(prefix: str, page_num: int, page_size: int) -> tuple[dict, str]:
    url = source_url(prefix, page_num, page_size)
    request = Request(url, headers={"User-Agent": "external-data-study-hktdc-hermes/1.0", "Accept": "text/html"})
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urlopen(request, timeout=40) as response:
                document = response.read().decode(response.headers.get_content_charset() or "utf-8")
            match = NEXT_DATA_RE.search(document)
            if not match:
                raise ValueError(f"page {page_num}: __NEXT_DATA__ was not found")
            page_props = json.loads(html.unescape(match.group(1)))["props"]["pageProps"]
            return page_props["exhibitorListData"], url
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise RuntimeError(f"page {page_num}: HTTP {error.code}") from error
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"page {page_num}: transport failed after 3 attempts") from last_error


def normalize(record: dict, position: int, url: str) -> dict[str, str]:
    record_id = str(record.get("id") or "").strip()
    name = " ".join(str(record.get("exhibitorName") or "").split())
    if not record_id:
        raise ValueError(f"record at position {position}: missing id")
    if not name:
        raise ValueError(f"record {record_id}: missing exhibitorName")
    return {
        "id": record_id,
        "exhibitor_name": name,
        "country": " ".join(str(record.get("countryDesc") or "").split()),
        "booth_numbers": json.dumps(record.get("boothNumbers") or [], ensure_ascii=False, separators=(",", ":")),
        "exhibitor_urn": str(record.get("exhibitorUrn") or ""),
        "supplier_urn": str(record.get("supplierUrn") or ""),
        "virtual_booth_url": str(record.get("vepVirtualBoothUrl") or ""),
        "contact_url": str(record.get("vepContactBtnUrl") or ""),
        "source_position": str(position),
        "source_url": url,
    }


def extract(prefix: str, page_size: int) -> list[dict[str, str]]:
    first_payload, first_url = fetch_page(prefix, 1, page_size)
    total = first_payload.get("totalSize")
    records = first_payload.get("data")
    if not isinstance(total, int) or total < 0 or not isinstance(records, list):
        raise ValueError("page 1: missing totalSize or data")
    if total and not records:
        raise ValueError("page 1: nonzero totalSize but zero records")
    pages = math.ceil(total / page_size) if total else 0
    rows: list[dict[str, str]] = []
    for page_num in range(1, pages + 1):
        payload, url = (first_payload, first_url) if page_num == 1 else fetch_page(prefix, page_num, page_size)
        if payload.get("totalSize") != total:
            raise ValueError(f"page {page_num}: totalSize differs from page 1")
        if payload.get("from") != (page_num - 1) * page_size:
            raise ValueError(f"page {page_num}: unexpected offset {payload.get('from')!r}")
        page_records = payload.get("data")
        if not isinstance(page_records, list) or (page_num < pages and not page_records):
            raise ValueError(f"page {page_num}: missing or unexpectedly empty data")
        rows.extend(normalize(record, len(rows) + 1, url) for record in page_records)
    if len(rows) != total:
        raise ValueError(f"expected {total} records, got {len(rows)}")
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate stable id(s) in extracted data")
    return rows


def atomic_write(path: Path, content: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as temp:
        temp.write(content)
        temp.flush()
        temp_path = Path(temp.name)
    temp_path.replace(path)


def write_outputs(prefix: str, rows: list[dict[str, str]]) -> tuple[Path, Path]:
    destination = OUTPUT_ROOT / prefix
    json_path = destination / f"hktdc_{prefix}_hermes.json"
    csv_path = destination / f"hktdc_{prefix}_hermes.csv"
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")
    csv_buffer = __import__("io").StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(csv_path, csv_buffer.getvalue(), "utf-8-sig")
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    if json_rows != csv_rows or any(tuple(row) != FIELDS for row in csv_rows):
        raise ValueError("CSV/JSON read-back equivalence failed")
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.prefix):
        parser.error("prefix must contain lowercase letters, digits, and hyphens only")
    if args.page_size != PAGE_SIZE:
        parser.error(f"page size is fixed at the observed native size: {PAGE_SIZE}")
    rows = extract(args.prefix, args.page_size)
    json_path, csv_path = write_outputs(args.prefix, rows)
    print(json.dumps({"prefix": args.prefix, "records": len(rows), "json": str(json_path.relative_to(ROOT)), "csv": str(csv_path.relative_to(ROOT))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
