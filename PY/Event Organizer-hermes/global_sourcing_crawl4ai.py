#!/usr/bin/env python3
"""Checkpointed public Global Sources exhibitor-profile extraction with Crawl4AI."""
from __future__ import annotations
import argparse, asyncio, csv, json, re, time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit, urlunsplit
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

TIMEOUT_MS = 60_000
RETRIES = 2


def canonical(url: str) -> str:
    p = urlsplit(url); return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def clean(value: str) -> str:
    return " ".join(value.split())


def section_text(soup: BeautifulSoup, heading: str) -> str:
    head = next((h for h in soup.find_all("h2") if clean(h.get_text(" ", strip=True)) == heading), None)
    if not head: return ""
    parts: list[str] = []
    for element in head.next_elements:
        if getattr(element, "name", None) == "h2": break
        if getattr(element, "name", None) in {"p", "h3", "li"}:
            text = clean(element.get_text(" ", strip=True))
            if text and text not in parts: parts.append(text)
    return " ".join(parts)


def parse(html: str, url: str, position: int) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    name = clean(soup.find("h1").get_text(" ", strip=True)) if soup.find("h1") else ""
    if not name: raise ValueError("missing exhibitor h1")
    header = clean(soup.find("h1").parent.get_text(" ", strip=True))
    country = re.search(r"Country/Region:\s*(.*?)\s*Business Type:", header)
    business = re.search(r"Business Type:\s*(.*?)(?:\s*Contact Us|$)", header)
    capabilities = clean(header.split("Country/Region:", 1)[0].removeprefix(name))
    overview = section_text(soup, "Company Overview:")
    show = section_text(soup, "Show Attending")
    return {"source_position": str(position), "source_url": url, "company name": name, "company": name,
            "company background": header, "other details": overview, "Business Type": clean(business.group(1)) if business else "",
            "Country/Region": clean(country.group(1)) if country else "", "Years of Establishment": "", "Major Market": "",
            "Cleaned_Background": overview, "Phase Attending": show, "Show Name": "Global Sources Hong Kong Shows",
            "capabilities": capabilities, "extraction_status": "extracted"}


async def fetch(url: str, position: int) -> dict[str, str]:
    last: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            config = BrowserConfig(headless=True, verbose=False, extra_args=["--disable-gpu", "--single-process"])
            async with AsyncWebCrawler(config=config) as crawler:
                result = await crawler.arun(url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=TIMEOUT_MS))
            if result.status_code == 403: return {"source_position": str(position), "source_url": url, "extraction_status": "blocked_403"}
            if result.status_code == 404: return {"source_position": str(position), "source_url": url, "extraction_status": "unavailable_404"}
            if not result.success or result.status_code != 200: raise RuntimeError(f"success={result.success}, status={result.status_code}")
            return parse(result.html, url, position)
        except Exception as exc:
            last = exc
            if attempt < RETRIES: await asyncio.sleep(attempt * 2)
    return {"source_position": str(position), "source_url": url, "extraction_status": "failed", "error": str(last)}


def write(path: Path, records: list[dict[str, str]]) -> None:
    fields = list(dict.fromkeys(k for row in records for k in row)); rows = [{k: str(row.get(k, "")) for k in fields} for row in records]
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        f.write("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)); temp = Path(f.name)
    temp.replace(path.with_suffix(".json"))
    with NamedTemporaryFile("w", encoding="utf-8-sig", newline="", dir=path.parent, delete=False) as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows); temp = Path(f.name)
    temp.replace(path.with_suffix(".csv"))

async def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--input", required=True); ap.add_argument("--output", required=True); ap.add_argument("--limit", type=int, help="optional bounded smoke-test limit"); args = ap.parse_args()
    with open(args.input, encoding="utf-8-sig", newline="") as f: urls = [canonical(r["full_url"]) for r in csv.DictReader(f) if r.get("full_url", "").strip()]
    if not urls: raise ValueError("no full_url values")
    seen=set(); urls=[u for u in urls if not (u in seen or seen.add(u))][:args.limit]
    output=Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = output.with_suffix(".checkpoint.jsonl")
    completed: dict[int, dict[str, str]] = {}
    if checkpoint.exists():
        for line_number, line in enumerate(checkpoint.read_text(encoding="utf-8").splitlines(), 1):
            row = json.loads(line); position = int(row.get("source_position", "0"))
            if not 1 <= position <= len(urls) or row.get("source_url") != urls[position - 1] or position in completed:
                raise ValueError(f"checkpoint line {line_number}: source identity mismatch or duplicate")
            completed[position] = row
    for i, url in enumerate(urls, 1):
        if i in completed:
            continue
        row=await fetch(url,i); completed[i] = row
        with checkpoint.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n"); handle.flush()
        print(json.dumps({"position":i,"total":len(urls),"status":row["extraction_status"]}),flush=True)
    records = [completed[i] for i in range(1, len(urls) + 1)]
    write(output, records)
    checkpoint.unlink()
    print(json.dumps({"records":len(records),"status_counts":{s:sum(r["extraction_status"]==s for r in records) for s in sorted({r["extraction_status"] for r in records})}}))
    return 0

if __name__ == "__main__": raise SystemExit(asyncio.run(main()))
