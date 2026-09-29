"""HKTDC L3 supplier-profile enrichment with Crawl4AI and aligned outcomes."""
from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / 'Result' / 'Exhibition Organizers' / 'HKTDC'
REQUEST_DELAY_SECONDS = 1
MAX_RETRIES = 2


def browser_config() -> BrowserConfig:
    return BrowserConfig(headless=True, verbose=False, extra_args=['--disable-gpu', '--single-process'])


def parse_supplier(html: str, l2: dict[str, str], url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, 'html.parser')
    record = {'source_company_name': l2.get('source_company_name', ''), 'supplier_url': url, 'l3_status': 'extracted'}
    card = soup.select_one('.item.css-19axa4z')
    if not card:
        raise ValueError(f'{url}: supplier detail card missing from HTTP 200 response')
    for child in card.select(':scope > div')[2:]:
        content = [part.strip() for part in child.get_text('\n', strip=True).split('\n') if part.strip()]
        key, values = '', []
        for item in content:
            if item.endswith(':'):
                if key and values: record[key] = ' '.join(values)
                key, values = item[:-1], []
            elif key:
                values.append(item)
        if key and values: record[key] = ' '.join(values)
    return record


async def fetch_one(l2: dict[str, str]) -> dict[str, str]:
    url = l2['supplier_url']
    if l2.get('l2_status') != 'extracted' or not url:
        return {'source_company_name': l2.get('source_company_name', ''), 'supplier_url': '', 'l3_status': 'not_attempted_l2_blocked'}
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with AsyncWebCrawler(config=browser_config()) as crawler:
                result = await crawler.arun(url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
            if result.status_code == 403:
                return {'source_company_name': l2.get('source_company_name', ''), 'supplier_url': url, 'l3_status': 'blocked_403'}
            if not result.success or result.status_code != 200:
                raise RuntimeError(f'{url}: success={result.success}, status={result.status_code}')
            return parse_supplier(result.html, l2, url)
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES: await asyncio.sleep(attempt * 2)
    raise RuntimeError(f'{url}: failed after {MAX_RETRIES} fresh-browser attempts: {last_error}')


async def extract(l2_records: list[dict[str, str]]) -> list[dict[str, str]]:
    records = []
    for position, l2 in enumerate(l2_records, start=1):
        row = await fetch_one(l2)
        records.append(row)
        print(f'Processing {position} out of {len(l2_records)}: {row["l3_status"]}', flush=True)
        # Do not impose a network delay when L2 was blocked and L3 made no request.
        if position < len(l2_records) and row['l3_status'] != 'not_attempted_l2_blocked':
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
    if len(records) != len(l2_records): raise ValueError('L3 alignment drift')
    return records


def write_artifacts(prefix: str, records: list[dict[str, str]]) -> None:
    out = OUTPUT_ROOT / prefix
    json_path, csv_path = out / f'hktdc_{prefix}_L3.json', out / f'hktdc_{prefix}_L3.csv'
    fields = list(dict.fromkeys(key for row in records for key in row))
    json_tmp, csv_tmp = json_path.with_suffix('.json.tmp'), csv_path.with_suffix('.csv.tmp')
    with json_tmp.open('w', encoding='utf-8') as handle:
        for row in records: handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    with csv_tmp.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n'); writer.writeheader(); writer.writerows(records)
    json_tmp.replace(json_path); csv_tmp.replace(csv_path)


def main() -> None:
    prefix = input('What is the prefix of your exhibition?').strip()
    l2_path = OUTPUT_ROOT / prefix / f'hktdc_{prefix}_L2.csv'
    with l2_path.open(encoding='utf-8-sig', newline='') as handle: l2_records = list(csv.DictReader(handle))
    if not l2_records or 'l2_status' not in l2_records[0]: raise ValueError('L2 is missing l2_status')
    records = asyncio.run(extract(l2_records))
    write_artifacts(prefix, records)
    counts = {status: sum(row['l3_status'] == status for row in records) for status in sorted({row['l3_status'] for row in records})}
    print(json.dumps({'records': len(records), 'status_counts': counts, 'stage': 'L3'}))


if __name__ == '__main__': main()
