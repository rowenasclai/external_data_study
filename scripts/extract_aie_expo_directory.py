#!/usr/bin/env python3
"""Extract the public AIE Expo online exhibitor directory deterministically."""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://admin.aie-expo.com/aie-admin-api/portal/getExhiCorpByCategory"
SOURCE_URL = "https://admin.aie-expo.com/aie-expo/pc"
SCOPES = ((1588, "Zhuhai Zone"), (1604, "Macao Zone"))
FIELDS = [
    "stable_id", "company_name", "company_name_local", "scope_id", "scope_label",
    "booth", "category", "address", "website", "detail_page_url", "source_url", "source_position",
]


def text(value: object) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split())


def parse_page(payload: object, *, scope_id: int, scope_label: str, page: int) -> tuple[list[dict[str, str]], int]:
    if not isinstance(payload, dict) or payload.get("code") != 200 or not isinstance(payload.get("data"), dict):
        raise ValueError("unexpected API envelope")
    data = payload["data"]
    total, items = data.get("total"), data.get("list")
    if not isinstance(total, int) or total < 0 or not isinstance(items, list):
        raise ValueError("missing total or list")
    rows = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("non-object exhibitor")
        ident = text(item.get("id"))
        name = text(item.get("exhiEnCompany") or item.get("exhiNameEn") or item.get("exhiCompany"))
        if not ident or not name:
            raise ValueError("exhibitor is missing stable ID or company name")
        local = text(item.get("exhiCompany"))
        # The same organization can legitimately participate in both public
        # zone scopes.  Identity is therefore participation-level: scope plus
        # the organizer's immutable exhibitor ID.
        rows.append({
            "stable_id": f"{scope_id}:{ident}",
            "company_name": name,
            "company_name_local": local,
            "scope_id": str(scope_id),
            "scope_label": scope_label,
            "booth": text(item.get("boothNo") or item.get("boothNum")),
            "category": text(item.get("categoryNameEn") or item.get("exhiCorpOneCategoryEn") or item.get("categoryName") or item.get("exhiCorpOneCategory")),
            "address": text(item.get("enRegisterAddress") or item.get("registerAddress")),
            "website": text(item.get("enWebsite") or item.get("website")),
            # The SPA route has no scope parameter and relies on client state;
            # do not publish an unverified constructed profile link.
            "detail_page_url": "",
            "source_url": SOURCE_URL,
            "source_position": "",  # assigned after stable native page order is complete
        })
    if total and not rows:
        raise ValueError(f"nonzero total with empty page {page}")
    return rows, total


def fetch(scope_id: int, page: int, page_size: int) -> object:
    query = urlencode({"pageNo": page, "pageSize": page_size, "expoId": scope_id})
    req = Request(f"{API}?{query}", headers={"User-Agent": "external-data-study-aie-extractor/1.0", "Accept": "application/json"})
    last = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt == 2:
                raise RuntimeError(f"page {page} scope {scope_id} failed after 3 attempts: {type(exc).__name__}") from exc
            time.sleep(1 << attempt)
    raise AssertionError(last)


def extract(page_size: int = 20) -> tuple[list[dict[str, str]], dict[str, int]]:
    combined, scope_totals = [], {}
    for scope_id, label in SCOPES:
        first, total = parse_page(fetch(scope_id, 1, page_size), scope_id=scope_id, scope_label=label, page=1)
        pages = (total + page_size - 1) // page_size
        rows = list(first)
        for page in range(2, pages + 1):
            current, current_total = parse_page(fetch(scope_id, page, page_size), scope_id=scope_id, scope_label=label, page=page)
            if current_total != total:
                raise ValueError(f"total drift in scope {scope_id}: {total} -> {current_total}")
            if page < pages and len(current) != page_size:
                raise ValueError(f"short interior page {page} in scope {scope_id}")
            rows.extend(current)
            time.sleep(0.15)
        if len(rows) != total:
            raise ValueError(f"scope {scope_id} count mismatch: {len(rows)} != {total}")
        ids = [r["stable_id"] for r in rows]
        duplicates = [ident for ident, count in Counter(ids).items() if count > 1]
        if duplicates:
            raise ValueError(f"duplicate IDs in scope {scope_id}: {duplicates[:5]}")
        scope_totals[label] = total
        combined.extend(rows)
    for position, row in enumerate(combined, 1):
        row["source_position"] = str(position)
    return combined, scope_totals


def atomic_write(rows: list[dict[str, str]], csv_path: Path, json_path: Path, scope_totals: dict[str, int]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    def stage(path: Path, content: str, encoding: str) -> Path:
        with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as f:
            f.write(content); f.flush(); os.fsync(f.fileno()); return Path(f.name)
    import io
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    csv_tmp = stage(csv_path, out.getvalue(), "utf-8-sig")
    payload = {"source_url": SOURCE_URL, "scope_totals": scope_totals, "reported_total": len(rows), "field_order": FIELDS, "records": rows}
    json_tmp = stage(json_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    csv_tmp.replace(csv_path); json_tmp.replace(json_path)


def readback(csv_path: Path, json_path: Path, expected: int) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); csv_rows = list(reader)
        if reader.fieldnames != FIELDS: raise ValueError("CSV field order drift")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if len(csv_rows) != expected or payload.get("records") != csv_rows or payload.get("reported_total") != expected:
        raise ValueError("CSV/JSON read-back mismatch")
    ids = [r["stable_id"] for r in csv_rows]
    if len(set(ids)) != len(ids) or any(not r["company_name"] for r in csv_rows):
        raise ValueError("post-write identity invariant failed")


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--output", type=Path, required=True); p.add_argument("--json-output", type=Path, required=True); args = p.parse_args()
    rows, totals = extract(); atomic_write(rows, args.output, args.json_output, totals); readback(args.output, args.json_output, len(rows))
    print(json.dumps({"records": len(rows), "scope_totals": totals, "csv": str(args.output), "json": str(args.json_output)}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
