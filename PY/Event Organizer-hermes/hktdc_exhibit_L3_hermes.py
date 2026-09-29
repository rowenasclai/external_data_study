#!/usr/bin/env python3
"""Checkpointable direct-HTTPS HKTDC L3 supplier-profile enrichment."""
from __future__ import annotations

import argparse
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "Result" / "Exhibition Organizers" / "HKTDC"
CONCURRENCY = 3
REQUEST_TIMEOUT_SECONDS = 45
MAX_RETRIES = 2


def outcome(l2: dict[str, str], status: str, url: str = "") -> dict[str, str]:
    return {"source_company_name": l2.get("source_company_name", ""), "supplier_url": url, "l3_status": status}


def parse_supplier(document: str, l2: dict[str, str], url: str) -> dict[str, str]:
    soup = BeautifulSoup(document, "html.parser")
    card = soup.select_one(".item.css-19axa4z")
    if not card:
        raise ValueError(f"{url}: supplier detail card missing from HTTP 200 response")
    record = outcome(l2, "extracted", url)
    for child in card.select(":scope > div")[2:]:
        parts = [part.strip() for part in child.get_text("\n", strip=True).split("\n") if part.strip()]
        key, values = "", []
        for part in parts:
            if part.endswith(":"):
                if key and values:
                    record[key] = " ".join(values)
                key, values = part[:-1], []
            elif key:
                values.append(part)
        if key and values:
            record[key] = " ".join(values)
    return record


def fetch_one(l2: dict[str, str]) -> dict[str, str]:
    url = l2.get("supplier_url", "")
    if l2.get("l2_status") != "extracted" or not url:
        return outcome(l2, "not_attempted_l2_unavailable")
    request = Request(url, headers={"User-Agent": "external-data-study-hktdc-hermes/1.0", "Accept": "text/html"})
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return parse_supplier(response.read().decode(response.headers.get_content_charset() or "utf-8"), l2, url)
        except HTTPError as error:
            if error.code == 403:
                return outcome(l2, "blocked_403", url)
            if error.code == 404:
                return outcome(l2, "unavailable_404", url)
            last_error = error
        except (URLError, TimeoutError) as error:
            last_error = error
        if attempt < MAX_RETRIES:
            time.sleep(attempt * 2)
    raise RuntimeError(f"{url}: failed after {MAX_RETRIES} direct HTTPS attempts: {last_error}")


def read_checkpoint(path: Path, l2_records: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    completed: dict[int, dict[str, str]] = {}
    if not path.exists():
        return completed
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        item = json.loads(line)
        position, record = item.get("position"), item.get("record")
        if not isinstance(position, int) or not isinstance(record, dict) or not 1 <= position <= len(l2_records):
            raise ValueError(f"checkpoint line {line_number}: invalid position/record")
        if item.get("supplier_url") != l2_records[position - 1].get("supplier_url", "") or position in completed:
            raise ValueError(f"checkpoint line {line_number}: L2 identity mismatch or duplicate position")
        completed[position] = record
    return completed


def append_checkpoint(path: Path, position: int, l2: dict[str, str], record: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"position": position, "supplier_url": l2.get("supplier_url", ""), "record": record}, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def atomic_write(path: Path, content: str, encoding: str) -> None:
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def write_artifacts(prefix: str, records: list[dict[str, str]]) -> None:
    output = OUTPUT_ROOT / prefix
    raw_normalized = [{key: "" if value is None else str(value) for key, value in row.items()} for row in records]
    fields = list(dict.fromkeys(key for row in raw_normalized for key in row))
    normalized = [{key: row.get(key, "") for key in fields} for row in raw_normalized]
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows(normalized)
    atomic_write(output / f"hktdc_{prefix}_L3.json", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in normalized), "utf-8")
    atomic_write(output / f"hktdc_{prefix}_L3.csv", buffer.getvalue(), "utf-8-sig")


def run(prefix: str, max_records: int | None) -> dict[str, object]:
    output = OUTPUT_ROOT / prefix
    with (output / f"hktdc_{prefix}_L2.csv").open(encoding="utf-8-sig", newline="") as handle:
        l2_records = list(csv.DictReader(handle))
    if not l2_records or "l2_status" not in l2_records[0]:
        raise ValueError("L2 is missing l2_status")
    checkpoint = output / f"hktdc_{prefix}_L3.checkpoint.jsonl"
    completed = read_checkpoint(checkpoint, l2_records)
    pending = [(position, row) for position, row in enumerate(l2_records, start=1) if position not in completed]
    if max_records is not None:
        pending = pending[:max_records]
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=CONCURRENCY, thread_name_prefix="hktdc-supplier") as pool:
        for offset in range(0, len(pending), CONCURRENCY):
            batch = pending[offset:offset + CONCURRENCY]
            futures = {pool.submit(fetch_one, row): (position, row) for position, row in batch}
            results = [(position, row, future.result()) for future, (position, row) in ((f, futures[f]) for f in as_completed(futures))]
            for position, row, record in sorted(results):
                append_checkpoint(checkpoint, position, row, record)
                completed[position] = record
                print(json.dumps({"position": position, "total": len(l2_records), "status": record["l3_status"]}), flush=True)
            if offset + CONCURRENCY < len(pending):
                time.sleep(1)
    if len(completed) == len(l2_records):
        write_artifacts(prefix, [completed[position] for position in range(1, len(l2_records) + 1)])
        checkpoint.unlink()
        status = "complete"
    else:
        status = "checkpointed"
    return {"prefix": prefix, "status": status, "completed": len(completed), "total": len(l2_records), "elapsed_seconds": round(time.monotonic() - started, 1)}


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
