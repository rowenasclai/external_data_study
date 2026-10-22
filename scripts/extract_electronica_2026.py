#!/usr/bin/env python3
"""Extract electronica 2026 public exhibitor directory and public profile pages."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

LANDING = "https://exhibitors.electronica.de/exhibitor-portal/2026/list-of-exhibitors/"
POST_URL = "https://exhibitors.electronica.de/prj_809/view/page.cfm"
EXPECTED_FIELDS = [
    "source_position", "listing_page", "company_name", "profile_url",
    "profile_title", "profile_description", "address", "website", "profile_sections",
]
USER_AGENT = "Mozilla/5.0 (compatible; electronica-public-directory-extractor/1.0)"
TIMEOUT = (10, 35)
DELAY = 0.25


def normalize(text: str) -> str:
    return " ".join(text.split())


def get_with_retry(session: requests.Session, url: str, *, data=None, headers=None) -> requests.Response:
    last = None
    for attempt in range(1, 4):
        try:
            response = session.post(url, data=data, headers=headers, timeout=TIMEOUT) if data is not None else session.get(url, headers=headers, timeout=TIMEOUT)
            if response.status_code in (408, 429, 500, 502, 503, 504):
                wait = min(30, 2 ** (attempt - 1))
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = min(60, int(retry_after))
                if attempt < 3:
                    time.sleep(wait)
                    continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last = exc
            if attempt < 3:
                time.sleep(min(30, 2 ** (attempt - 1)))
    if last:
        raise RuntimeError(f"request failed after bounded retries: {urlparse_path(url)} ({last.__class__.__name__})") from last
    raise RuntimeError(f"HTTP request failed after bounded retries: {urlparse_path(url)}")


def urlparse_path(url: str) -> str:
    from urllib.parse import urlsplit
    return urlsplit(url).path


def parse_listing(html_text: str) -> tuple[list[dict[str, str]], int | None, int | None]:
    soup = BeautifulSoup(html_text, "html.parser")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.select('a[href*="/exhibitordetails/"]'):
        card = anchor.find_parent(class_="pb_ce")
        if card and "advert" in (card.get("class") or []):
            continue
        name = normalize(anchor.get_text(" ", strip=True))
        href = urljoin(LANDING, anchor.get("href", ""))
        if name and href not in seen:
            rows.append({"company_name": name, "profile_url": href})
            seen.add(href)
    total = None
    page_count = None
    form = soup.select_one("form#paging_1")
    if form:
        btn = form.find("input", attrs={"name": "SRField", "type": "submit"})
        if btn and str(btn.get("value", "")).isdigit():
            page_count = int(btn["value"])
        # The hidden selector field is named StartRow_query_res_<page-count> and
        # stores the final result row. Resolve it by the independently displayed page count.
        if page_count:
            count_field = form.find("input", attrs={"name": f"StartRow_query_res_{page_count}"})
            if count_field and str(count_field.get("value", "")).isdigit():
                total = int(count_field["value"])
    return rows, total, page_count


def paging_payload(html_text: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html_text, "html.parser")
    form = soup.select_one("form#paging_1")
    if not form:
        raise ValueError("pagination form paging_1 missing")
    fields = []
    for inp in form.select("input[name][value]"):
        if inp.has_attr("disabled") or inp.get("type") == "image":
            continue
        fields.append((inp["name"], inp["value"]))
    fields.extend([("SRField_next", "next"), ("nvp", "search")])
    return fields


def parse_profile(session: requests.Session, row: dict[str, object]) -> dict[str, object]:
    response = get_with_retry(session, str(row["profile_url"]))
    soup = BeautifulSoup(response.text, "html.parser")
    row["profile_title"] = normalize(soup.title.get_text(" ", strip=True)) if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    row["profile_description"] = meta.get("content", "") if meta else ""
    for key, selector in (("address", ".ce_addr"), ("website", ".ce_website a")):
        vals = []
        for node in soup.select(selector):
            value = normalize(node.get_text(" ", strip=True))
            if value and value not in vals:
                vals.append(value)
        row[key] = " | ".join(vals)
    sections = []
    modules = soup.find_all(class_=lambda c: c and any(x.startswith("mod_") for x in ([c] if isinstance(c, str) else c)))
    for module in modules:
        heading = module.select_one(".mo_header h1, .mo_header h2, .mo_title")
        content = module.select_one(".mo_content")
        if heading and content:
            text = normalize(content.get_text(" ", strip=True))
            if text:
                item = normalize(heading.get_text(" ", strip=True)) + ": " + text
                if item not in sections:
                    sections.append(item)
    row["profile_sections"] = "\n".join(sections)
    return row


def load_checkpoint(path: Path) -> dict[int, dict[str, object]]:
    done: dict[int, dict[str, object]] = {}
    if not path.exists():
        return done
    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                pos = int(row["source_position"])
                if pos in done:
                    raise ValueError("duplicate position")
                done[pos] = row
            except Exception as exc:
                raise ValueError(f"invalid checkpoint line {line_no}; preserve and inspect before resuming") from exc
    return done


def atomic_json(path: Path, data: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_outputs(rows: list[dict[str, object]], outdir: Path, total: int, page_count: int) -> None:
    csv_path = outdir / "electronica_2026_exhibitors.csv"
    json_path = outdir / "electronica_2026_exhibitors.json"
    for path, writer in ((csv_path, "csv"), (json_path, "json")):
        tmp = path.with_suffix(path.suffix + ".tmp")
        if writer == "csv":
            with tmp.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=EXPECTED_FIELDS, lineterminator="\n", extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
        else:
            ordered_rows = [{key: row.get(key, "") for key in EXPECTED_FIELDS} for row in rows]
            tmp.write_text(json.dumps(ordered_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    report = {
        "source": LANDING,
        "reported_total": total,
        "reported_pages": page_count,
        "pagination_derived_total": page_count * 15,
        "records": len(rows),
        "unique_profile_urls": len({r["profile_url"] for r in rows}),
        "profile_field_coverage": {key: sum(bool(r.get(key)) for r in rows) for key in ("address", "website", "profile_description", "profile_sections")},
        "source_count_discrepancy": (page_count * 15) - total,
        "csv": csv_path.name,
        "json": json_path.name,
        "complete": len(rows) == page_count * 15 and len({r["profile_url"] for r in rows}) == page_count * 15,
    }
    atomic_json(outdir / "electronica_2026_extraction_report.json", report)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--limit-pages", type=int, default=0, help="test only the first N listing pages; 0 means all")
    args = ap.parse_args()
    outdir = args.output_dir
    outdir.mkdir(parents=True, exist_ok=True)
    checkpoint = outdir / "electronica_2026_profiles.checkpoint.jsonl"
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    initial = get_with_retry(session, LANDING)
    html_text = initial.text
    _, total, page_count = parse_listing(html_text)
    if not total or not page_count:
        raise RuntimeError("could not read public directory total/page count")
    target_total = page_count * 15
    required_pages = min(page_count, args.limit_pages) if args.limit_pages else page_count
    baseline: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    listing_pages = []
    for page_no in range(1, required_pages + 1):
        items, current_total, current_pages = parse_listing(html_text)
        if current_total != total or current_pages != page_count:
            raise RuntimeError(f"directory metadata changed on listing page {page_no}: total/pages={current_total}/{current_pages}")
        # Live contract reports 3,616 records but exposes 242 native 15-row pages
        # (3,630 page slots); preserve that discrepancy and validate every returned ID.
        expected_len = 15
        if len(items) != expected_len:
            raise RuntimeError(f"listing page {page_no}: expected {expected_len} records from native page size, parsed {len(items)}")
        for item in items:
            if item["profile_url"] in seen_urls:
                raise RuntimeError(f"duplicate profile URL on listing page {page_no}")
            seen_urls.add(item["profile_url"])
            item["listing_page"] = page_no
            baseline.append(item)
        listing_pages.append({"page": page_no, "records": len(items), "first": items[0]["company_name"], "last": items[-1]["company_name"]})
        print(json.dumps({"stage": "listing", "page": page_no, "pages": required_pages, "records": len(baseline)}), flush=True)
        if page_no < required_pages:
            payload = paging_payload(html_text)
            time.sleep(DELAY)
            html_text = get_with_retry(session, POST_URL, data=payload, headers={"Referer": LANDING, "X-Requested-With": "XMLHttpRequest"}).text
    atomic_json(outdir / "electronica_2026_listing_pages.json", listing_pages)
    if not args.limit_pages and len(baseline) != target_total:
        raise RuntimeError(f"pagination coverage mismatch: {len(baseline)} != page-derived {target_total}; source reports {total}")
    done = load_checkpoint(checkpoint)
    for pos, row in done.items():
        if not 1 <= pos <= len(baseline) or row.get("profile_url") != baseline[pos - 1]["profile_url"] or row.get("company_name") != baseline[pos - 1]["company_name"]:
            raise RuntimeError(f"checkpoint identity mismatch at position {pos}")
    with checkpoint.open("a", encoding="utf-8") as log:
        for pos, item in enumerate(baseline, 1):
            if pos in done:
                continue
            row: dict[str, object] = {"source_position": pos, **item}
            try:
                parse_profile(session, row)
            except Exception as exc:
                print(json.dumps({"stage": "profile", "position": pos, "url": urlparse_path(str(item["profile_url"])), "error": type(exc).__name__}), flush=True)
                raise
            log.write(json.dumps(row, ensure_ascii=False) + "\n")
            log.flush()
            done[pos] = row
            if pos % 25 == 0 or pos == len(baseline):
                print(json.dumps({"stage": "profiles", "completed": len(done), "target": len(baseline)}), flush=True)
            time.sleep(DELAY)
    rows = [done[pos] for pos in range(1, len(baseline) + 1)]
    if not args.limit_pages and (len(rows) != target_total or len(done) != target_total):
        raise RuntimeError(f"incomplete profile pass: {len(rows)} / {target_total} (source metadata reports {total})")
    write_outputs(rows, outdir, total, page_count)
    print(json.dumps({"stage": "complete", "records": len(rows), "reported_total": total, "pagination_derived_total": target_total, "source_count_discrepancy": target_total - total, "limited_pages": args.limit_pages or None, "output_dir": str(outdir)}), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
