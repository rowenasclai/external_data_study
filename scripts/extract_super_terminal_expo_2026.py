#!/usr/bin/env python3
"""Extract the public Super Terminal Expo 2026 exhibitor directory.

The directory's public DataTables contract reports an immutable ExhibitorID and
50 records across its native 24-record pages.  No credentials/cookies are used.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LANDING_URL = "https://exhibitors.informamarkets-info.com/event/STE2026"
API_URL = "https://exhibitors.informamarkets-info.com/api"
PAGE_SIZE = 24
FIELDS = ["exhibitor_id", "company_name", "booth_no", "country", "profile_url", "source_url", "source_position"]
USER_AGENT = "external-data-study-super-terminal-expo-extractor/1.0"


def request_page(start: int, *, timeout: int = 30, retries: int = 2) -> dict[str, Any]:
    params = {
        "fn": "getExhibitor", "orderfields": '["FeaturedExhibitor","ExhibitorNameEn","StandNoStr","CountryEn"]',
        "order[0][column]": "0", "order[0][dir]": "desc", "order[1][column]": "1", "order[1][dir]": "asc",
        "start": str(start), "length": str(PAGE_SIZE), "draw": "1", "dt": "1", "SearchLog": "1",
        "FairID": "bQ917tdgAVE0MCu4AxIXSg==", "FairCode": "j11wWcMy5+GpWGT27L0mAA==",
        "DefineCountry": "False", "UseOldCountry": "False", "MyList": "0", "Email": "",
        "Url": LANDING_URL, "HideEmptyProducts": "0",
    }
    url = f"{API_URL}?{urlencode(params)}"
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Referer": LANDING_URL})
            with urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError(f"page start={start}: unexpected HTTP {response.status}")
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            transient = not isinstance(exc, HTTPError) or exc.code in {408, 429, 500, 502, 503, 504}
            if not transient or attempt == retries:
                raise RuntimeError(f"page start={start}, attempt={attempt + 1}: request failed") from exc
            time.sleep(min(4, 2 ** attempt))
    raise AssertionError("unreachable")


def parse_page(payload: dict[str, Any]) -> tuple[list[dict[str, str]], int]:
    try:
        total = int(payload["recordsTotal"])
        records = payload["data"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("directory response lacks recordsTotal or data") from exc
    if total < 0 or not isinstance(records, list) or (total and not records):
        raise ValueError("directory response has invalid total/data combination")
    rows = []
    for item in records:
        ident = str(item.get("ExhibitorID", "")).strip()
        name = " ".join(str(item.get("ExhibitorNameEn", "")).split())
        if not ident or not name:
            raise ValueError("directory row lacks immutable ExhibitorID or company name")
        friendly = str(item.get("FriendlyUrl", "")).strip()
        profile = f"{LANDING_URL}/en-US/exhibitor/{friendly}" if friendly else ""
        rows.append({
            "exhibitor_id": ident, "company_name": name,
            "booth_no": " ".join(str(item.get("StandNoStr", "")).split()),
            "country": " ".join(str(item.get("CountryEn", "")).split()),
            "profile_url": profile, "source_url": LANDING_URL, "source_position": "",
        })
    return rows, total


def validate(rows: list[dict[str, str]], total: int, page_starts: list[int]) -> None:
    expected_starts = list(range(0, total, PAGE_SIZE))
    if page_starts != expected_starts or len(rows) != total:
        raise ValueError(f"incomplete pagination: rows={len(rows)} total={total} pages={page_starts}")
    ids = [row["exhibitor_id"] for row in rows]
    duplicates = [ident for ident, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate exhibitor IDs: {duplicates[:5]}")
    if any(not row["company_name"] for row in rows):
        raise ValueError("blank company name")


def write_artifacts(rows: list[dict[str, str]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "super_terminal_expo_2026_exhibitors.csv"
    json_path = output_dir / "super_terminal_expo_2026_exhibitors.json"
    for index, row in enumerate(rows, 1): row["source_position"] = str(index)
    for path, writer in ((csv_path, "csv"), (json_path, "json")):
        fd, temporary_name = tempfile.mkstemp(dir=output_dir, prefix=f".{path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig" if writer == "csv" else "utf-8", newline="") as handle:
                if writer == "csv":
                    out = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
                    out.writeheader(); out.writerows(rows)
                else:
                    json.dump(rows, handle, ensure_ascii=False, indent=2); handle.write("\n")
                handle.flush(); os.fsync(handle.fileno())
            Path(temporary_name).replace(path)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True); raise
    return csv_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("Result/Other Events/Super Terminal Expo 2026"))
    args = parser.parse_args()
    first_rows, total = parse_page(request_page(0))
    pages: dict[int, list[dict[str, str]]] = {0: first_rows}
    for start in range(PAGE_SIZE, total, PAGE_SIZE):
        rows, repeated_total = parse_page(request_page(start))
        if repeated_total != total or not rows: raise ValueError(f"page start={start}: changed total or empty interior page")
        pages[start] = rows
    ordered = [row for start in sorted(pages) for row in pages[start]]
    validate(ordered, total, sorted(pages))
    csv_path, json_path = write_artifacts(ordered, args.output_dir)
    print(json.dumps({"records": total, "csv": str(csv_path), "json": str(json_path)}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
