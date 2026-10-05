#!/usr/bin/env python3
"""Extract the public GovWare 2026 Sponsors & Exhibitors directory."""
import argparse
import csv
import html
import io
import json
import re
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

LISTING_URL = "https://www.govware.sg/visit/govware-2026-sponsors-exhibitors"
BASE_URL = "https://www.govware.sg/"
FIELDS = ["source_position", "exhibitor_id", "company_name", "booth", "sponsorship_tiers", "profile_url", "logo_url", "company_description", "company_website", "products_services_solutions", "source_url", "extraction_status"]


def clean(value):
    return " ".join(html.unescape(value or "").split())


def fetch(url, retries=2):
    error = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "external-data-study-exhibitor/1.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            error = exc
            if attempt == retries:
                raise RuntimeError(f"request failed for {url}: {exc}") from exc
            time.sleep(1.0 * (attempt + 1))
    raise error


class ListingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.current = [], None
        self.capture = None

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        classes = attr.get("class", "")
        if tag == "li" and "m-exhibitors-list__items__item" in classes and attr.get("data-content-i-d"):
            self.current = {"exhibitor_id": attr["data-content-i-d"], "company_name": "", "booth": "", "profile_path": "", "logo_url": "", "sponsorship_tier": ""}
            match = re.search(r"--status-([^\s]+)", classes)
            self.current["sponsorship_tier"] = clean(match.group(1).replace("–", "-").replace("-", " ").title()) if match else ""
        if not self.current:
            return
        if tag == "h2" and "header__title" in classes:
            self.capture = "company_name"
        elif tag == "div" and "header__meta__stand" in classes:
            self.capture = "booth"
        elif tag == "a":
            match = re.search(r"openRemoteModal\('([^']+)'", attr.get("href", ""))
            if match:
                self.current["profile_path"] = match.group(1)
        elif tag == "div" and "items__item__image" in classes:
            match = re.search(r"url\(['\"]([^'\"]+)['\"]\)", attr.get("style") or "")
            if match:
                self.current["logo_url"] = match.group(1)

    def handle_endtag(self, tag):
        if tag in {"h2", "div"}:
            self.capture = None
        if tag == "li" and self.current:
            row = self.current
            self.current = None
            if row["company_name"] and row["profile_path"]:
                row["company_name"] = clean(row["company_name"])
                row["booth"] = re.sub(r"^Booth:\s*", "", clean(row["booth"]), flags=re.I)
                self.rows.append(row)

    def handle_data(self, data):
        if self.current and self.capture:
            self.current[self.capture] += data


def parse_listing(document):
    totals = [int(x) for x in re.findall(r'data-totalcount="(\d+)"', document)]
    if not totals:
        raise ValueError("missing published exhibitor group totals")
    parser = ListingParser()
    parser.feed(document)
    if len(parser.rows) != sum(totals):
        raise ValueError(f"listing row count {len(parser.rows)} != published group total {sum(totals)}")
    return parser.rows, sum(totals)


def profile_fields(document):
    def one(pattern):
        match = re.search(pattern, document, re.I | re.S)
        return clean(re.sub(r"<[^>]+>", " ", match.group(1))) if match else ""
    name = one(r'<h1[^>]*header__infos__title[^>]*>(.*?)</h1>')
    booth = one(r'<div[^>]*header__infos__stand[^>]*>(.*?)</div>').removeprefix("Booth:").strip()
    description = one(r'<div[^>]*body__description[^>]*>(.*?)</div>')
    website_match = re.search(r'<div[^>]*header__logo[^>]*>.*?<a\s+href=[\"\'](https?://[^\"\']+)', document, re.I | re.S)
    website = clean(website_match.group(1)) if website_match else ""
    products = one(r'Products,\s*Services\s*&amp;\s*Solutions.*?additional__item__value[^>]*>(.*?)</div>')
    return {"company_name": name, "booth": booth, "company_description": description, "company_website": website, "products_services_solutions": products}


def atomic_write(path, content, encoding):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding=encoding, newline="", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()
    listing, published_occurrences = parse_listing(fetch(LISTING_URL))
    grouped = {}
    for item in listing:
        bucket = grouped.setdefault(item["exhibitor_id"], item | {"sponsorship_tiers": []})
        if item["sponsorship_tier"] and item["sponsorship_tier"] not in bucket["sponsorship_tiers"]:
            bucket["sponsorship_tiers"].append(item["sponsorship_tier"])
    rows = []
    for position, item in enumerate(grouped.values(), 1):
        profile_url = BASE_URL + item["profile_path"].lstrip("/")
        detail = profile_fields(fetch(profile_url))
        if clean(detail["company_name"]).casefold() != clean(item["company_name"]).casefold():
            raise ValueError(f"profile name mismatch for ID {item['exhibitor_id']}")
        if detail["booth"] and item["booth"] and detail["booth"] != item["booth"]:
            raise ValueError(f"profile booth mismatch for ID {item['exhibitor_id']}")
        rows.append({"source_position": str(position), "exhibitor_id": item["exhibitor_id"], "company_name": item["company_name"], "booth": item["booth"], "sponsorship_tiers": "; ".join(item["sponsorship_tiers"]), "profile_url": profile_url, "logo_url": item["logo_url"], "company_description": detail["company_description"], "company_website": detail["company_website"], "products_services_solutions": detail["products_services_solutions"], "source_url": LISTING_URL, "extraction_status": "extracted"})
        time.sleep(args.delay)
    if len(rows) != len(grouped) or len({r["exhibitor_id"] for r in rows}) != len(rows) or any(not r["company_name"] for r in rows):
        raise ValueError("identity or required-field validation failed")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    csv_path = args.output_dir / "govware_2026_exhibitors.csv"
    json_path = args.output_dir / "govware_2026_exhibitors.json"
    atomic_write(csv_path, stream.getvalue(), "utf-8-sig")
    atomic_write(json_path, json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    if csv_rows != json_rows:
        raise ValueError("CSV/JSON read-back mismatch")
    print(json.dumps({"published_occurrences": published_occurrences, "unique_exhibitors": len(rows), "status_counts": Counter(r["extraction_status"] for r in rows), "csv_json_equivalent": True}, default=dict))

if __name__ == "__main__":
    main()
