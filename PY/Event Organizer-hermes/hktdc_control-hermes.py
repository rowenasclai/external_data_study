#!/usr/bin/env python3
"""Select imminent HKTDC exhibitions and run the isolated Hermes extractor.

Defaults to the version-controlled control CSV. A public Google Sheets CSV export
may be supplied with --control-csv-url once the owner provides one; it is fetched
at run time and is never stored locally.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTROL_CSV = ROOT / "Result" / "Exhibition Organizers" / "HKTDC" / "Event_Schedule" / "event_control.csv"
EXTRACTOR = Path(__file__).with_name("hktdc_exhibit-hermes.py")
TIMEZONE = ZoneInfo("Asia/Hong_Kong")
LEAD_DAYS = (3, 7, 10, 14, 30)
PREFIX_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_FORMATS = ("%m/%d/%y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S")


def read_csv_text(control_csv_url: str | None) -> str:
    if control_csv_url:
        request = Request(control_csv_url, headers={"User-Agent": "external-data-study-hktdc-hermes/1.0"})
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    return DEFAULT_CONTROL_CSV.read_text(encoding="utf-8-sig")


def parse_start_date(value: str) -> date:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unsupported event_start_date: {value!r}")


def select_events(rows: list[dict[str, str]], today: date) -> list[dict[str, str]]:
    targets = {today + timedelta(days=days) for days in LEAD_DAYS}
    selected: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=2):
        prefix = (row.get("prefix") or "").strip()
        if not prefix:
            continue
        if not PREFIX_RE.fullmatch(prefix):
            raise ValueError(f"row {row_number}: invalid prefix {prefix!r}")
        start_date = parse_start_date(row.get("event_start_date") or "")
        if start_date in targets:
            selected.append({**row, "prefix": prefix, "event_start_date": start_date.isoformat()})
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-csv-url", help="public CSV URL, e.g. a Google Sheets published CSV export")
    parser.add_argument("--as-of", help="Hong Kong date for deterministic validation (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="select and report only; do not extract")
    args = parser.parse_args()

    today = date.fromisoformat(args.as_of) if args.as_of else datetime.now(TIMEZONE).date()
    rows = list(csv.DictReader(io.StringIO(read_csv_text(args.control_csv_url))))
    selected = select_events(rows, today)
    summary = {
        "as_of_hkt": today.isoformat(),
        "lead_days": list(LEAD_DAYS),
        "control_source": args.control_csv_url or str(DEFAULT_CONTROL_CSV.relative_to(ROOT)),
        "selected_prefixes": [row["prefix"] for row in selected],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if args.dry_run:
        return 0
    if not EXTRACTOR.is_file():
        raise FileNotFoundError(f"missing extractor: {EXTRACTOR}")
    for row in selected:
        subprocess.run([sys.executable, str(EXTRACTOR), "--prefix", row["prefix"]], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
