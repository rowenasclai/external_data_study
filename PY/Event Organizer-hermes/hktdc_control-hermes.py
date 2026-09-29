#!/usr/bin/env python3
"""Hermes-safe controller for the portable HKTDC L1/L2/L3 pipeline.

This is the unattended counterpart to ``PY/Event Organizer/hktdc_control.py``.
It keeps the same imminent-event rule, but uses repository-relative paths,
explicit runtimes, a non-interactive child interface, bounded subprocesses,
and fail-closed stage propagation.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
LEGACY_DIR = ROOT / "PY" / "Event Organizer"
CONTROL_CSV = ROOT / "Result" / "Exhibition Organizers" / "HKTDC" / "Event_Schedule" / "event_control.csv"
CRAWL_PYTHON = ROOT / ".venv-crawl4ai" / "bin" / "python"
PLAYWRIGHT_PYTHON = ROOT / ".venv-playwright" / "bin" / "python"
BROWSER_PATH = ROOT / ".playwright-browsers"
TIMEZONE = ZoneInfo("Asia/Hong_Kong")
LEAD_DAYS = (3, 7, 10, 14, 30)
DATE_FORMATS = ("%m/%d/%y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S")
STAGES = (
    ("L1", CRAWL_PYTHON, "hktdc_exhibit_L1.py"),
    ("L2", CRAWL_PYTHON, "hktdc_exhibit_L2.py"),
    ("L3", CRAWL_PYTHON, "hktdc_exhibit_L3.py"),
    ("format", PLAYWRIGHT_PYTHON, "hktdc_format.py"),
)


def parse_start_date(value: str) -> date:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unsupported event_start_date: {value!r}")


def select_events(rows: list[dict[str, str]], today: date) -> list[str]:
    selected: list[str] = []
    target_dates = {today + timedelta(days=days) for days in LEAD_DAYS}
    for row_number, row in enumerate(rows, start=2):
        prefix = (row.get("prefix") or "").strip()
        if not prefix:
            continue
        if not prefix.replace("-", "").isalnum() or prefix.lower() != prefix:
            raise ValueError(f"row {row_number}: invalid prefix {prefix!r}")
        if parse_start_date(row.get("event_start_date") or "") in target_dates:
            selected.append(prefix)
    return selected


def child_environment() -> dict[str, str]:
    if not BROWSER_PATH.is_dir():
        raise RuntimeError(f"missing repository-local browser runtime: {BROWSER_PATH}")
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    # Crawl4AI is in its dedicated venv while its compatible Pandas/Pydantic
    # stack is installed in the repository Playwright venv.  Replace inherited
    # agent paths rather than appending them, avoiding incompatible system wheels.
    env["PYTHONPATH"] = str(ROOT / ".venv-playwright" / "lib" / "python3.14" / "site-packages")
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_PATH)
    return env


def run_stage(stage: str, interpreter: Path, script_name: str, prefix: str, env: dict[str, str], timeout: int) -> dict[str, object]:
    script = LEGACY_DIR / script_name
    if not interpreter.is_file() or not script.is_file():
        raise RuntimeError(f"{stage}: missing interpreter or script")
    command = [str(interpreter), str(script)]
    try:
        completed = subprocess.run(
            command, input=prefix + "\n", text=True,
            cwd=LEGACY_DIR, env=env, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        result = {"stage": stage, "status": "timed_out", "timeout_seconds": timeout,
                  "stdout": (error.stdout or "")[-2000:], "stderr": (error.stderr or "")[-2000:]}
        raise RuntimeError(json.dumps(result, ensure_ascii=False, default=str)) from error
    result = {"stage": stage, "returncode": completed.returncode, "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]}
    if completed.returncode:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", help="deterministic HKT date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="select events only")
    parser.add_argument("--prefix", action="append", help="explicit prefix; may be supplied more than once")
    parser.add_argument("--stage-timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.stage_timeout <= 0:
        parser.error("--stage-timeout must be positive")
    today = date.fromisoformat(args.as_of) if args.as_of else datetime.now(TIMEZONE).date()
    with CONTROL_CSV.open(encoding="utf-8-sig", newline="") as handle:
        selected = select_events(list(csv.DictReader(handle)), today)
    if args.prefix:
        selected = list(dict.fromkeys(args.prefix))
    print(json.dumps({"as_of_hkt": today.isoformat(), "lead_days": LEAD_DAYS, "selected_prefixes": selected, "dry_run": args.dry_run}))
    if args.dry_run:
        return 0
    env = child_environment()
    for prefix in selected:
        for stage, interpreter, script_name in STAGES:
            run_stage(stage, interpreter, script_name, prefix, env, args.stage_timeout)
            print(json.dumps({"prefix": prefix, "stage": stage, "status": "passed"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
