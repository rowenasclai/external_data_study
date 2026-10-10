#!/usr/bin/env python3
"""Checkpointable direct-HTTPS HKTDC L2 enrichment.

Uses public server-rendered detail HTML rather than a browser.  It preserves
L1 identity for extracted, blocked, and unavailable detail-page outcomes, and
writes final L2 artifacts only after all positions reconcile.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "Result" / "Exhibition Organizers" / "HKTDC"
DOMAIN = "https://www.hktdc.com"
CONCURRENCY = 3
REQUEST_TIMEOUT_SECONDS = 45
MAX_RETRIES = 2


def canonical_exhibitor_url(url: str) -> str:
    parts = urlsplit(urljoin(DOMAIN, url))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def outcome_record(l1: dict[str, str], url: str, status: str) -> dict[str, str]:
    return {"source_company_name": l1["Company Name"], "source_location": l1["Location"], "supplier_url": "", "exhibitor_url": url, "l2_status": status}


def parse_detail(document: str, l1: dict[str, str], url: str) -> dict[str, str]:
    soup = BeautifulSoup(document, "html.parser")
    card = soup.select_one(".d-flex.flex-column.col-12")
    if not card:
        raise ValueError(f"{url}: detail card missing from HTTP 200 response")
    record = outcome_record(l1, url, "extracted")
    booth = card.select_one('span[class*="exhibitors_formatDtl"]')
    if booth:
        record["Booth"] = booth.get_text(" ", strip=True)
    for label in card.select("span.text-level-detail-caption.text-font-bold"):
        value = label.find_next("span", class_="text-font-normal")
        if value:
            record[label.get_text(" ", strip=True)] = value.get_text(" ", strip=True)
    supplier = next((a.get("href") for a in card.select("a[href]") if "View more about this company" in a.get_text(" ", strip=True)), "")
    record["supplier_url"] = urljoin(DOMAIN, supplier) if supplier else ""
    return record


def fetch_one(l1: dict[str, str]) -> dict[str, str]:
    url = canonical_exhibitor_url(l1["url"])
    request = Request(url, headers={"User-Agent": "external-data-study-hktdc-hermes/1.0", "Accept": "text/html"})
    last_error: Exception | None = None
    terminal_status = "request_error"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return parse_detail(response.read().decode(response.headers.get_content_charset() or "utf-8"), l1, url)
        except HTTPError as error:
            if error.code == 403:
                return outcome_record(l1, url, "blocked_403")
            if error.code == 404:
                return outcome_record(l1, url, "unavailable_404")
            last_error = error
            terminal_status = f"request_error_http_{error.code}"
        except (URLError, TimeoutError) as error:
            last_error = error
        except ValueError as error:
            last_error = error
            terminal_status = "parse_error"
        if attempt < MAX_RETRIES:
            time.sleep(attempt * 2)
    # A single public endpoint failure must not discard the L1 identity or
    # prevent the remaining checkpointed records from completing.
    return outcome_record(l1, url, terminal_status)


def read_checkpoint(path: Path, l1_records: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    completed: dict[int, dict[str, str]] = {}
    if not path.exists():
        return completed
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        item = json.loads(line)
        position, record = item.get("position"), item.get("record")
        if not isinstance(position, int) or not isinstance(record, dict) or not 1 <= position <= len(l1_records):
            raise ValueError(f"checkpoint line {line_number}: invalid position/record")
        if item.get("exhibitor_url") != l1_records[position - 1]["url"] or position in completed:
            raise ValueError(f"checkpoint line {line_number}: L1 identity mismatch or duplicate position")
        completed[position] = record
    return completed


def append_checkpoint(path: Path, position: int, l1: dict[str, str], record: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"position": position, "exhibitor_url": l1["url"], "record": record}, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write(path: Path, content: str, encoding: str) -> None:
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def write_artifacts(prefix: str, records: list[dict[str, str]]) -> None:
    output = OUTPUT_ROOT / prefix
    # CSV represents absent values as empty strings; normalize JSON the same way
    # so read-back equivalence is deterministic across direct and resumed records.
    raw_normalized = [{key: "" if value is None else str(value) for key, value in row.items()} for row in records]
    fields = list(dict.fromkeys(key for row in raw_normalized for key in row))
    # Materialize absent optional fields as blanks in both formats.
    normalized = [{key: row.get(key, "") for key in fields} for row in raw_normalized]
    json_content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in normalized)
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows(normalized)
    atomic_write(output / f"hktdc_{prefix}_L2.json", json_content, "utf-8")
    atomic_write(output / f"hktdc_{prefix}_L2.csv", buffer.getvalue(), "utf-8-sig")


def run(prefix: str, max_records: int | None) -> dict[str, object]:
    output = OUTPUT_ROOT / prefix
    with (output / f"hktdc_{prefix}_L1.csv").open(encoding="utf-8-sig", newline="") as handle:
        l1_records = list(csv.DictReader(handle))
    required = {"Company Name", "Location", "url"}
    if not l1_records or not required.issubset(l1_records[0]) or any(not row["url"] for row in l1_records):
        raise ValueError("L1 is missing required identity fields")
    checkpoint = output / f"hktdc_{prefix}_L2.checkpoint.jsonl"
    completed = read_checkpoint(checkpoint, l1_records)
    pending = [(position, row) for position, row in enumerate(l1_records, start=1) if position not in completed]
    if max_records is not None:
        pending = pending[:max_records]
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=CONCURRENCY, thread_name_prefix="hktdc-direct") as pool:
        for offset in range(0, len(pending), CONCURRENCY):
            batch = pending[offset:offset + CONCURRENCY]
            futures = {pool.submit(fetch_one, row): (position, row) for position, row in batch}
            results = []
            for future in as_completed(futures):
                position, row = futures[future]
                results.append((position, row, future.result()))
            for position, row, record in sorted(results):
                append_checkpoint(checkpoint, position, row, record)
                completed[position] = record
                print(json.dumps({"position": position, "total": len(l1_records), "status": record["l2_status"]}), flush=True)
            if offset + CONCURRENCY < len(pending):
                time.sleep(1)
    if len(completed) == len(l1_records):
        records = [completed[position] for position in range(1, len(l1_records) + 1)]
        write_artifacts(prefix, records)
        checkpoint.unlink()
        status = "complete"
    else:
        status = "checkpointed"
    return {"prefix": prefix, "status": status, "completed": len(completed), "total": len(l1_records), "elapsed_seconds": round(time.monotonic() - started, 1)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--max-records", type=int, help="bounded smoke run; final artifact withheld")
    args = parser.parse_args()
    if args.max_records is not None and args.max_records <= 0:
        parser.error("--max-records must be positive")
    print(json.dumps(run(args.prefix, args.max_records)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
