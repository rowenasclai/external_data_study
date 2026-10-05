#!/usr/bin/env python3
"""Extract the public GovWare 2026 sponsors and exhibitors directory.

The official single-page directory is server-rendered.  It exposes each record
through an ASP Events ``openRemoteModal('exhibitors/<stable-slug>', ...)``
link, so no login, browser state, or private API is needed.  The page does not
publish a total or pagination; the extractor therefore validates the complete
single-page listing and retains one row per published stable slug.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE_URL = "https://www.govware.sg/visit/govware-2026-sponsors-exhibitors"
USER_AGENT = "external-data-study-govware-exhibitor-extractor/1.0"
FIELDS = ("exhibitor_id", "company_name", "detail_url", "source_url", "source_position")
MODAL_ID = re.compile(r"openRemoteModal\(\\?'exhibitors/([a-z0-9-]+)\\?'", re.I)


def clean(value: str) -> str:
    return " ".join(html.unescape(value).split())


class DirectoryParser(HTMLParser):
    """Collect visible names bound to the official source's modal stable IDs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._anchors: list[tuple[str, list[str]]] = []
        self.items: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href") or ""
            self._anchors.append((href, []))

    def handle_data(self, data: str) -> None:
        if self._anchors:
            self._anchors[-1][1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._anchors:
            return
        href, fragments = self._anchors.pop()
        match = MODAL_ID.search(href)
        name = clean("".join(fragments))
        if match and name:
            self.items.append((match.group(1), name))


def parse_directory(payload: str) -> tuple[list[dict[str, str]], int]:
    """Return unique ordered rows and the count of exact repeat source cards.

    The official page uses some repeated visual cards.  A repeated stable slug
    is accepted only where its normalized displayed name is identical; a
    conflicting name is a source-contract failure, rather than silently
    choosing one of the values.
    """
    parser = DirectoryParser()
    parser.feed(payload)
    parser.close()
    if not parser.items:
        raise ValueError("GovWare directory contains no named exhibitor modal links")
    seen: dict[str, str] = {}
    rows: list[dict[str, str]] = []
    repeats = 0
    for exhibitor_id, company_name in parser.items:
        previous = seen.get(exhibitor_id)
        if previous is not None:
            if previous != company_name:
                raise ValueError(f"stable ID {exhibitor_id!r} has conflicting names")
            repeats += 1
            continue
        seen[exhibitor_id] = company_name
        rows.append(
            {
                "exhibitor_id": exhibitor_id,
                "company_name": company_name,
                "detail_url": "",
                "source_url": SOURCE_URL,
                "source_position": "",
            }
        )
    if not rows:
        raise ValueError("GovWare directory contains zero unique exhibitors")
    if len(seen) != len(rows):
        raise ValueError("internal stable-ID uniqueness failure")
    return rows, repeats


def fetch_source(retries: int = 2) -> str:
    request = Request(SOURCE_URL, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise RuntimeError(f"GovWare directory HTTP {response.status}")
                payload = response.read().decode(response.headers.get_content_charset() or "utf-8")
            return payload
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise RuntimeError(f"GovWare directory HTTP {error.code}") from error
            if attempt < retries:
                time.sleep(min(4, 2**attempt))
    raise RuntimeError("GovWare directory failed after bounded retries") from last_error


def validate_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("cannot write zero GovWare exhibitors")
    ids = [row["exhibitor_id"] for row in rows]
    duplicates = [item for item, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate exhibitor IDs: {duplicates[:10]}")
    for row in rows:
        if not clean(row["company_name"]):
            raise ValueError(f"exhibitor {row['exhibitor_id']!r} has no company name")
        if row["source_url"] != SOURCE_URL:
            raise ValueError("unexpected source URL")


def atomic_write(path: Path, content: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as handle:
        handle.write(content)
        handle.flush()
        temporary = Path(handle.name)
    temporary.replace(path)


def write_outputs(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    validate_rows(rows)
    csv_buffer = __import__("io").StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(csv_path, csv_buffer.getvalue(), "utf-8-sig")
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")


def validate_artifacts(csv_path: Path, json_path: Path) -> int:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
        if tuple(handle.seek(0) or next(csv.reader(handle))) != FIELDS:
            raise ValueError("CSV header/order differs from required schema")
    loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(loaded_json, list) or any(tuple(row) != FIELDS for row in loaded_json):
        raise ValueError("JSON schema/order differs from required schema")
    if csv_rows != loaded_json:
        raise ValueError("CSV/JSON field-for-field equivalence failed")
    validate_rows(csv_rows)
    return len(csv_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()
    rows, repeats = parse_directory(fetch_source())
    for position, row in enumerate(rows, start=1):
        row["source_position"] = str(position)
    validate_rows(rows)
    write_outputs(rows, args.output, args.json_output)
    count = validate_artifacts(args.output, args.json_output)
    print(f"source_rows={count + repeats} unique_rows={count} exact_repeat_cards={repeats} csv={args.output} json={args.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
