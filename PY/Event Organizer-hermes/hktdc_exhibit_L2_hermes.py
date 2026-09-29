#!/usr/bin/env python3
"""Checkpointable HKTDC L2 runner with one browser session per 100 records.

Completed records are checkpointed against their L1 position and source URL.
A final L2 artifact is written only after complete L1/L2 reconciliation.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT / "PY" / "Event Organizer" / "hktdc_exhibit_L2.py"
OUTPUT_ROOT = ROOT / "Result" / "Exhibition Organizers" / "HKTDC"
SESSION_RECORDS = 100
PAGE_TIMEOUT_MS = 60_000


def load_legacy():
    spec = importlib.util.spec_from_file_location("hktdc_l2_legacy", LEGACY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {LEGACY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


async def fetch_in_session(legacy, crawler, l1: dict[str, str]) -> dict[str, str]:
    url = legacy.canonical_exhibitor_url(l1["url"])
    result = await crawler.arun(url, config=legacy.CrawlerRunConfig(cache_mode=legacy.CacheMode.BYPASS, page_timeout=PAGE_TIMEOUT_MS))
    if result.status_code == 403:
        return legacy.blocked_record(l1, url, 403)
    if not result.success or result.status_code != 200:
        raise RuntimeError(f"{url}: success={result.success}, status={result.status_code}")
    return legacy.parse_detail(result.html, l1, url)


async def run(prefix: str, max_records: int | None) -> dict[str, int | str]:
    legacy = load_legacy()
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
    sessions: list[list[tuple[int, dict[str, str]]]] = []
    for entry in pending:
        bucket = (entry[0] - 1) // SESSION_RECORDS
        if not sessions or (sessions[-1][0][0] - 1) // SESSION_RECORDS != bucket:
            sessions.append([])
        sessions[-1].append(entry)
    for session_index, session in enumerate(sessions, start=1):
        first_position = session[0][0]
        print(json.dumps({"session": session_index, "position_range": [first_position, session[-1][0]], "session_records": len(session), "session_policy": "new browser every 100 source records"}), flush=True)
        async with legacy.AsyncWebCrawler(config=legacy.browser_config()) as crawler:
            for position, row in session:
                record = await fetch_in_session(legacy, crawler, row)
                append_checkpoint(checkpoint, position, row, record)
                completed[position] = record
                print(json.dumps({"position": position, "total": len(l1_records), "status": record["l2_status"]}), flush=True)
                if position != len(l1_records):
                    await asyncio.sleep(legacy.REQUEST_DELAY_SECONDS)
    if len(completed) == len(l1_records):
        legacy.write_artifacts(prefix, [completed[position] for position in range(1, len(l1_records) + 1)])
        checkpoint.unlink()
        status = "complete"
    else:
        status = "checkpointed"
    return {"prefix": prefix, "status": status, "completed": len(completed), "total": len(l1_records), "elapsed_seconds": round(time.monotonic() - started, 1)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--max-records", type=int, help="bounded smoke/benchmark run; final output is withheld")
    args = parser.parse_args()
    if args.max_records is not None and args.max_records <= 0:
        parser.error("--max-records must be positive")
    print(json.dumps(asyncio.run(run(args.prefix, args.max_records))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
