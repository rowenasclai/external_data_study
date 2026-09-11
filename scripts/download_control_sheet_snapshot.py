#!/usr/bin/env python3
"""Download a reproducible public CSV snapshot of the exhibition control sheet."""
from __future__ import annotations
import argparse
import csv
import io
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen

SOURCE_URL = "https://docs.google.com/spreadsheets/d/1WJHV8bBeiCJbY-zo5zFDUuYoUH_LNXPHuIqUlPqP0II/export?format=csv"
REQUIRED_HEADERS = {"Event Name", "Status", "Extracted File Name"}


def download() -> bytes:
    request = Request(SOURCE_URL, headers={"User-Agent": "external-data-study-control-sheet-snapshot/1.0"})
    with urlopen(request, timeout=45) as response:
        content = response.read()
    if not content:
        raise ValueError("control sheet export was empty")
    return content


def validate(content: bytes) -> None:
    text = content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    for row in rows:
        if REQUIRED_HEADERS.issubset(set(row)):
            return
    raise ValueError("control sheet export lacks required headers")


def write(content: bytes, output: Path) -> bool:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.read_bytes() == content:
        return False
    with NamedTemporaryFile("wb", dir=output.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(output)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    content = download()
    validate(content)
    print(f"snapshot_changed={write(content, args.output)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
