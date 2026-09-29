#!/usr/bin/env python3
"""Hermes-safe daily controller for the HKTDC L1/L2/L3/format pipeline."""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
LEGACY_DIR = ROOT / "PY" / "Event Organizer"
HERE = Path(__file__).resolve().parent
CONTROL_CSV = ROOT / "Result" / "Exhibition Organizers" / "HKTDC" / "Event_Schedule" / "event_control.csv"
CRAWL_PYTHON = ROOT / ".venv-crawl4ai" / "bin" / "python"
PLAYWRIGHT_PYTHON = ROOT / ".venv-playwright" / "bin" / "python"
BROWSER_PATH = ROOT / ".playwright-browsers"
TIMEZONE = ZoneInfo("Asia/Hong_Kong")
LEAD_DAYS = (3, 7, 10, 14, 30)
DATE_FORMATS = ("%m/%d/%y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S")
STAGES = (
    ("L1", CRAWL_PYTHON, LEGACY_DIR / "hktdc_exhibit_L1.py", "interactive"),
    ("L2", PLAYWRIGHT_PYTHON, HERE / "hktdc_exhibit_L2_hermes.py", "argument"),
    ("L3", PLAYWRIGHT_PYTHON, HERE / "hktdc_exhibit_L3_hermes.py", "argument"),
    ("format", PLAYWRIGHT_PYTHON, HERE / "hktdc_format_hermes.py", "argument"),
)


def parse_start_date(value: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unsupported event_start_date: {value!r}")


def select_events(rows: list[dict[str, str]], today: date) -> list[str]:
    targets = {today + timedelta(days=days) for days in LEAD_DAYS}
    selected = []
    for row_number, row in enumerate(rows, start=2):
        prefix = (row.get("prefix") or "").strip()
        if not prefix:
            continue
        if not prefix.replace("-", "").isalnum() or prefix.lower() != prefix:
            raise ValueError(f"row {row_number}: invalid prefix {prefix!r}")
        if parse_start_date(row.get("event_start_date") or "") in targets:
            selected.append(prefix)
    return selected


def child_environment() -> dict[str, str]:
    if not BROWSER_PATH.is_dir():
        raise RuntimeError(f"missing repository-local browser runtime: {BROWSER_PATH}")
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env["PYTHONPATH"] = str(ROOT / ".venv-playwright" / "lib" / "python3.14" / "site-packages")
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_PATH)
    return env


def run_stage(name: str, interpreter: Path, script: Path, mode: str, prefix: str, env: dict[str, str], timeout: int) -> None:
    if not interpreter.is_file() or not script.is_file():
        raise RuntimeError(f"{name}: missing interpreter or script")
    command = [str(interpreter), str(script)]
    kwargs: dict[str, object] = {"cwd": ROOT, "env": env, "text": True, "capture_output": True, "timeout": timeout}
    if mode == "interactive":
        kwargs["input"] = prefix + "\n"
    else:
        command.extend(["--prefix", prefix])
    try:
        completed = subprocess.run(command, **kwargs)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(json.dumps({"stage": name, "status": "timed_out", "timeout_seconds": timeout, "stdout": (error.stdout or "")[-2000:], "stderr": (error.stderr or "")[-2000:]}, default=str)) from error
    if completed.returncode:
        raise RuntimeError(json.dumps({"stage": name, "returncode": completed.returncode, "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]}, ensure_ascii=False))
    print(json.dumps({"prefix": prefix, "stage": name, "status": "passed"}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", help="deterministic Hong Kong date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prefix", action="append", help="explicit prefix; repeatable")
    parser.add_argument("--stage-timeout", type=int, default=7200)
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
        for stage in STAGES:
            run_stage(*stage, prefix, env, args.stage_timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
