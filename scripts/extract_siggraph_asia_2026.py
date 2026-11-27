#!/usr/bin/env python3
"""Extract the public SIGGRAPH Asia 2026 participating-companies table."""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen

SOURCE_URL = "https://asia.siggraph.org/2026/program/visit-exhibition/"
FIELDS = ("exhibitor_id", "company_name", "sponsor_type", "booth", "country", "remarks", "detail_url", "source_url", "source_position")


def clean(value: str) -> str:
    return " ".join(html.unescape(value).split())


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table": self.table = []
        elif tag == "tr" and self.table is not None: self.row = []
        elif tag in ("td", "th") and self.row is not None: self.cell = []

    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(clean("".join(self.cell))); self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            self.table.append(self.row); self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table); self.table = None


def parse(html_text: str) -> list[dict[str, str]]:
    parser = TableParser(); parser.feed(html_text); parser.close()
    table = next((t for t in parser.tables if t and [x.casefold() for x in t[0]] == ["sponsor", "exhibitor / sponsor", "booth no.", "country", "remarks"]), None)
    if table is None: raise ValueError("SIGGRAPH 2026 participating-companies table not found")
    rows=[]
    for position, cells in enumerate(table[1:], start=1):
        if len(cells) != 5: raise ValueError(f"row {position} has {len(cells)} cells")
        sponsor, name, booth, country, remarks = cells
        if not name: raise ValueError(f"row {position} has blank company name")
        rows.append({"exhibitor_id": f"siggraph-asia-2026:{position}", "company_name":name, "sponsor_type":sponsor, "booth":booth, "country":country, "remarks":remarks, "detail_url":"", "source_url":SOURCE_URL, "source_position":str(position)})
    if not rows: raise ValueError("SIGGRAPH table has no records")
    if len({r['exhibitor_id'] for r in rows}) != len(rows): raise ValueError("duplicate stable IDs")
    return rows


def atomic_write(path: Path, content: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as f:
        f.write(content); f.flush(); os.fsync(f.fileno()); tmp=Path(f.name)
    tmp.replace(path)


def write(rows, csv_path: Path, json_path: Path) -> None:
    from io import StringIO
    csv_buffer=StringIO(newline=""); writer=csv.DictWriter(csv_buffer, fieldnames=FIELDS, lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    atomic_write(csv_path, csv_buffer.getvalue(), "utf-8-sig")
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2)+"\n", "utf-8")


def validate(csv_path: Path, json_path: Path) -> int:
    with csv_path.open(encoding="utf-8-sig", newline="") as f: csv_rows=list(csv.DictReader(f)); fields=tuple(csv_rows[0]) if csv_rows else ()
    json_rows=json.loads(json_path.read_text(encoding="utf-8"))
    if fields != FIELDS or csv_rows != json_rows: raise ValueError("CSV/JSON mismatch")
    if not csv_rows or any(not r['company_name'] for r in csv_rows): raise ValueError("missing names")
    if len({r['exhibitor_id'] for r in csv_rows}) != len(csv_rows): raise ValueError("duplicate IDs")
    return len(csv_rows)


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output", type=Path, required=True); ap.add_argument("--json-output", type=Path, required=True); args=ap.parse_args()
    request=Request(SOURCE_URL, headers={"User-Agent":"external-data-study-siggraph-2026/1.0", "Accept":"text/html"})
    with urlopen(request, timeout=45) as response:
        if response.status != 200: raise RuntimeError(f"HTTP {response.status}")
        payload=response.read().decode(response.headers.get_content_charset() or "utf-8", errors="strict")
    rows=parse(payload); write(rows,args.output,args.json_output); print(f"rows={validate(args.output,args.json_output)} source={SOURCE_URL}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
