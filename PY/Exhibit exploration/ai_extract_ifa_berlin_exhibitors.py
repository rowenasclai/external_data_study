#!/usr/bin/env python3
"""Extract IFA Berlin 2026 exhibitors from the public server-rendered directory.

The source is paginated HTML at https://www.ifa-berlin.com/exhibitors?page=N.
No login, cookies, or browser automation are required.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

SOURCE_URL = "https://www.ifa-berlin.com/exhibitors"
USER_AGENT = "external-data-study-ifa-exhibitor-extractor/1.0"
FIELDS = (
    "exhibitor_id", "company_name", "country", "show_areas", "halls", "booths",
    "profile_description", "website_url", "detail_url", "logo_url", "source_page", "source_position",
)
PROFILE_DESCRIPTION_RE = re.compile(r'<div class="description">(.*?)</div>', re.S)
PROFILE_LINK_RE = re.compile(r'<div class="social-link-text"><a href="([^"]+)"', re.S)
SOCIAL_HOSTS = ("facebook.com", "instagram.com", "linkedin.com", "tiktok.com", "twitter.com", "x.com", "youtube.com")


def clean(value: str) -> str:
    return " ".join(html.unescape(value).split())


class ListingParser(HTMLParser):
    """Parse public IFA exhibitor cards without third-party dependencies."""

    def __init__(self, source_page: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_page = source_page
        self.rows: list[dict[str, str]] = []
        self.current: dict[str, Any] | None = None
        self.card_depth = 0
        self.capture: str | None = None
        self.capture_depth = 0
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if self.current is not None and tag == "div":
            self.card_depth += 1
        if tag == "div" and "brand-card" in classes and self.current is None:
            self.current = {"show_areas": [], "halls": [], "booths": []}
            self.card_depth = 1
            return
        if self.current is None:
            return
        if tag == "a" and "list-item-link" in classes:
            self.current["detail_url"] = urljoin(self.source_page, values.get("href") or "")
        elif tag == "img" and not self.current.get("logo_url"):
            source = values.get("src") or ""
            self.current["logo_url"] = urljoin(self.source_page, source) if source else ""
        elif tag == "button" and values.get("data-entity-id"):
            self.current["exhibitor_id"] = values["data-entity-id"] or ""
        elif tag == "div":
            label = None
            if "name" in classes:
                label = "company_name"
            elif "country" in classes:
                label = "country"
            elif "show-area" in classes:
                label = "show_area"
            elif "brand-location-hall" in classes:
                label = "hall"
            elif "brand-location-stand" in classes:
                label = "booth"
            if label:
                self.capture = label
                self.capture_depth = self.card_depth
                self.text = []

    def handle_data(self, data: str) -> None:
        if self.current is not None and self.capture:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if tag == "div" and self.capture and self.card_depth == self.capture_depth:
            value = clean("".join(self.text))
            if value:
                target = {"show_area": "show_areas", "hall": "halls", "booth": "booths"}.get(self.capture, self.capture)
                if target in ("show_areas", "halls", "booths"):
                    self.current[target].append(value)
                else:
                    self.current[target] = value
            self.capture = None
            self.text = []
        if tag == "div":
            self.card_depth -= 1
            if self.card_depth == 0:
                self._finish_card()

    def _finish_card(self) -> None:
        assert self.current is not None
        required = ("exhibitor_id", "company_name")
        missing = [field for field in required if not clean(str(self.current.get(field) or ""))]
        if missing:
            raise ValueError(f"IFA exhibitor card missing {', '.join(missing)}")
        self.rows.append(
            {
                "exhibitor_id": clean(str(self.current["exhibitor_id"])),
                "company_name": clean(str(self.current["company_name"])),
                "country": clean(str(self.current.get("country") or "")),
                "show_areas": " | ".join(dict.fromkeys(self.current["show_areas"])),
                "halls": " | ".join(dict.fromkeys(self.current["halls"])),
                "booths": " | ".join(dict.fromkeys(self.current["booths"])),
                "detail_url": str(self.current.get("detail_url") or ""),
                "logo_url": str(self.current.get("logo_url") or ""),
                "source_page": self.source_page,
            }
        )
        self.current = None
        self.card_depth = 0
        self.capture = None
        self.text = []


def parse_listing(html_text: str, source_page: str) -> tuple[list[dict[str, str]], int]:
    parser = ListingParser(source_page)
    parser.feed(html_text)
    parser.close()
    if parser.current is not None:
        raise ValueError("IFA listing ended with an incomplete exhibitor card")
    pages = [int(value) for value in re.findall(r'href="\?page=(\d+)"', html_text)]
    if not pages:
        raise ValueError("IFA listing does not expose pagination")
    if not parser.rows:
        raise ValueError("IFA listing contains no exhibitor cards")
    return parser.rows, max(pages)


def page_url(page_number: int) -> str:
    return SOURCE_URL if page_number == 1 else f"{SOURCE_URL}?{urlencode({'page': page_number})}"


def text_from_fragment(fragment: str) -> str:
    collector = HTMLParser(convert_charrefs=True)
    chunks: list[str] = []
    collector.handle_data = chunks.append  # type: ignore[method-assign]
    collector.feed(fragment)
    collector.close()
    return clean(" ".join(chunks))


def parse_profile(html_text: str) -> tuple[str, str]:
    """Return the published company description and first non-social website URL."""
    description_match = PROFILE_DESCRIPTION_RE.search(html_text)
    description = text_from_fragment(description_match.group(1)) if description_match else ""
    website = ""
    for href in PROFILE_LINK_RE.findall(html_text):
        lowered = href.lower()
        if href.startswith(("http://", "https://")) and not any(host in lowered for host in SOCIAL_HOSTS):
            website = html.unescape(href)
            break
    return description, website


def fetch_profile(url: str, retries: int = 2) -> tuple[str, str]:
    time.sleep(0.5)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=40) as response:
                if response.status != 200:
                    raise RuntimeError(f"profile {url}: HTTP {response.status}")
                payload = response.read().decode(response.headers.get_content_charset() or "utf-8")
            return parse_profile(payload)
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise RuntimeError(f"profile {url}: HTTP {error.code}") from error
            if attempt < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"profile {url} failed after {retries + 1} attempts") from last_error


def enrich_profiles(rows: list[dict[str, str]], workers: int = 3) -> None:
    """Fetch public profile pages with bounded concurrency, preserving source order."""
    targets = [(index, row["detail_url"]) for index, row in enumerate(rows) if row["detail_url"]]
    for row in rows:
        row["profile_description"] = ""
        row["website_url"] = ""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_profile, url): index for index, url in targets}
        for completed, future in enumerate(as_completed(futures), start=1):
            index = futures[future]
            description, website = future.result()
            rows[index]["profile_description"] = description
            rows[index]["website_url"] = website
            if completed % 100 == 0 or completed == len(targets):
                print(f"Fetched {completed}/{len(targets)} public exhibitor profiles")


def fetch_page(page_number: int, retries: int = 2) -> tuple[list[dict[str, str]], int, str]:
    url = page_url(page_number)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=40) as response:
                if response.status != 200:
                    raise RuntimeError(f"page {page_number}: HTTP {response.status}")
                payload = response.read().decode(response.headers.get_content_charset() or "utf-8")
            rows, page_count = parse_listing(payload, url)
            return rows, page_count, url
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                raise RuntimeError(f"page {page_number}: HTTP {error.code}") from error
            if attempt < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"page {page_number} failed after {retries + 1} attempts") from last_error


def extract() -> list[dict[str, str]]:
    first_rows, total_pages, _ = fetch_page(1)
    ordered = first_rows
    for page_number in range(2, total_pages + 1):
        time.sleep(0.15)
        rows, observed_pages, _ = fetch_page(page_number)
        if observed_pages != total_pages:
            raise ValueError(f"page {page_number}: pagination changed from {total_pages} to {observed_pages}")
        if not rows:
            raise ValueError(f"page {page_number}: unexpectedly empty")
        ordered.extend(rows)
    ids = [row["exhibitor_id"] for row in ordered]
    if len(ids) != len(set(ids)):
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        raise ValueError(f"duplicate exhibitor IDs: {', '.join(duplicates[:10])}")
    for position, row in enumerate(ordered, start=1):
        row["source_position"] = str(position)
    enrich_profiles(ordered)
    return ordered


def atomic_write(path: Path, content: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def write_outputs(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    if not rows:
        raise ValueError("no rows to write")
    csv_buffer = __import__("io").StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(csv_path, csv_buffer.getvalue(), "utf-8-sig")
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if csv_rows != json_rows or any(tuple(row) != FIELDS for row in csv_rows):
        raise ValueError("CSV/JSON read-back equivalence failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()
    rows = extract()
    write_outputs(rows, args.output, args.json_output)
    print(json.dumps({"records": len(rows), "csv": str(args.output), "json": str(args.json_output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
