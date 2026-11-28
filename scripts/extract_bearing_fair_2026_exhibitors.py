#!/usr/bin/env python3
"""Extract the public BEARING 2026 exhibitor-list notices.

The organizer publishes the complete list as seven numbered public HTML notices,
rather than an API.  It reuses some booth codes, including within one notice,
so each stable record identifier is the explicit compound
``notice-number:booth:source-name``.  No login, cookies, or credentials are
used.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LISTING_URL = "http://www.bearingfair.cn/eindex.php/index/lists"
BASE_URL = "http://www.bearingfair.cn"
USER_AGENT = "external-data-study-bearing-2026-exhibitor-extractor/1.0"
FIELDS = ("exhibitor_id", "booth", "company_name_zh", "company_name_en", "source_group", "detail_url", "source_position")
NOTICE_RE = re.compile(r'<h4 class="pg-blog-item-title"><a href="([^"]+)">\s*(BEARING 2026 EXHIBITORS LIST ([1-9][0-9]*))\s*</a>', re.I)
DETAIL_RE = re.compile(r'<div class="pg-blog-item blog-details text-center">(.*?)</div>\s*<div class="col-xl-3', re.I | re.S)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
BOOTH_RE = re.compile(r"^([0-9A-Z]+)\s+(.+)$")


class ExtractionError(RuntimeError):
    pass


def clean(fragment: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", fragment)).replace("\xa0", " ").split())


def fetch(url: str, retries: int = 2) -> str:
    last_error: Exception | None = None
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=40) as response:
                if response.status != 200:
                    raise ExtractionError(f"HTTP {response.status} for {url}")
                return response.read().decode(response.headers.get_content_charset() or "utf-8", "strict")
        except HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504):
                raise ExtractionError(f"HTTP {exc.code} for {url}") from exc
            last_error = exc
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(1 + attempt)
    raise ExtractionError(f"request failed after {retries + 1} attempts for {url}: {type(last_error).__name__}") from last_error


def parse_listing(page: str) -> list[tuple[int, str]]:
    notices: list[tuple[int, str]] = []
    for href, _title, number in NOTICE_RE.findall(page):
        notices.append((int(number), BASE_URL + html.unescape(href)))
    notices.sort()
    numbers = [number for number, _url in notices]
    if not notices or numbers != list(range(1, max(numbers) + 1)):
        raise ExtractionError(f"numbered 2026 list notices are not contiguous: {numbers}")
    if len(set(url for _number, url in notices)) != len(notices):
        raise ExtractionError("duplicate detail notice URLs")
    return notices


def parse_detail(page: str, group: int, detail_url: str) -> list[dict[str, str]]:
    container = DETAIL_RE.search(page)
    if not container:
        raise ExtractionError(f"notice {group} lacks its detail container")
    rows: list[dict[str, str]] = []
    for fragment in P_RE.findall(container.group(1)):
        text = clean(fragment)
        if not text:
            continue
        match = BOOTH_RE.match(text)
        if not match:
            raise ExtractionError(f"notice {group} has unparsable exhibitor row: {text[:100]!r}")
        booth, names = match.groups()
        # The official notice uses tab/spacing between Chinese and English names.
        # Preserve a single source name if no robust bilingual boundary exists.
        pieces = re.split(r"\s{2,}", names, maxsplit=1)
        zh = pieces[0].strip()
        en = pieces[1].strip() if len(pieces) == 2 else ""
        if not zh:
            raise ExtractionError(f"notice {group} has a blank company name for booth {booth}")
        # Retain every source occurrence: the organizer's booth labels alone
        # are not unique across the seven official published notices.
        identifier = f"{group}:{booth}:{zh}"
        rows.append({"exhibitor_id": identifier, "booth": booth, "company_name_zh": zh, "company_name_en": en, "source_group": str(group), "detail_url": detail_url})
    if not rows:
        raise ExtractionError(f"notice {group} contains no exhibitor records")
    return rows


def validate(rows: list[dict[str, str]], expected_groups: list[int]) -> None:
    if not rows:
        raise ExtractionError("no exhibitors extracted")
    ids = [row["exhibitor_id"] for row in rows]
    if len(ids) != len(set(ids)):
        duplicates = sorted({item for item in ids if ids.count(item) > 1})[:10]
        raise ExtractionError(f"duplicate booth IDs: {duplicates}")
    groups = sorted({int(row["source_group"]) for row in rows})
    if groups != expected_groups:
        raise ExtractionError(f"source group coverage mismatch: {groups} != {expected_groups}")
    for row in rows:
        if not row["company_name_zh"] or not row["detail_url"] or not row["booth"]:
            raise ExtractionError("required record field is blank")


def atomic_write(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [{field: row.get(field, "") for field in FIELDS} for row in rows]
    temporary: list[Path] = []
    try:
        with NamedTemporaryFile("w", encoding="utf-8-sig", newline="", dir=csv_path.parent, delete=False) as handle:
            temporary.append(Path(handle.name))
            csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n").writeheader()
            csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n").writerows(ordered)
            handle.flush(); os.fsync(handle.fileno())
        with NamedTemporaryFile("w", encoding="utf-8", newline="", dir=json_path.parent, delete=False) as handle:
            temporary.append(Path(handle.name))
            json.dump(ordered, handle, ensure_ascii=False, indent=2); handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary.pop(0), csv_path)
        os.replace(temporary.pop(0), json_path)
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)


def readback(csv_path: Path, json_path: Path, expected_groups: list[int]) -> None:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if not csv_rows or tuple(csv_rows[0]) != FIELDS or csv_rows != json_rows:
        raise ExtractionError("CSV/JSON read-back equivalence failed")
    validate(csv_rows, expected_groups)


def run(csv_path: Path, json_path: Path) -> int:
    notices = parse_listing(fetch(LISTING_URL))
    all_rows: list[dict[str, str]] = []
    for ordinal, (group, url) in enumerate(notices):
        all_rows.extend(parse_detail(fetch(url), group, url))
        if ordinal + 1 < len(notices):
            time.sleep(0.25)
    for position, row in enumerate(all_rows, 1):
        row["source_position"] = str(position)
    expected_groups = [group for group, _url in notices]
    validate(all_rows, expected_groups)
    atomic_write(all_rows, csv_path, json_path)
    readback(csv_path, json_path, expected_groups)
    print(json.dumps({"records": len(all_rows), "groups": expected_groups, "csv": str(csv_path), "json": str(json_path)}, ensure_ascii=False))
    return len(all_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()
    run(args.output, args.json_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
