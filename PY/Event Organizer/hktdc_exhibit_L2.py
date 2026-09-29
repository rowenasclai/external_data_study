"""HKTDC L2 public detail enrichment with Crawl4AI and explicit outcomes."""
from __future__ import annotations

import asyncio
import csv
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / 'Result' / 'Exhibition Organizers' / 'HKTDC'
DOMAIN = 'https://www.hktdc.com'
REQUEST_DELAY_SECONDS = 1
MAX_RETRIES = 2
BATCH_SIZE = 3
QUEUE_SIZE = 10


def canonical_exhibitor_url(url: str) -> str:
    parts = urlsplit(urljoin(DOMAIN, url))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


def blocked_record(l1: dict[str, str], url: str, status: int) -> dict[str, str]:
    return {'source_company_name': l1['Company Name'], 'source_location': l1['Location'], 'supplier_url': '', 'exhibitor_url': url, 'l2_status': f'blocked_{status}'}


def parse_detail(html: str, l1: dict[str, str], url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, 'html.parser')
    card = soup.select_one('.d-flex.flex-column.col-12')
    if not card:
        raise ValueError(f'{url}: detail card missing from HTTP 200 response')
    record = {'source_company_name': l1['Company Name'], 'source_location': l1['Location'], 'supplier_url': '', 'exhibitor_url': url, 'l2_status': 'extracted'}
    booth = card.select_one('span[class*="exhibitors_formatDtl"]')
    if booth:
        record['Booth'] = booth.get_text(' ', strip=True)
    for label in card.select('span.text-level-detail-caption.text-font-bold'):
        value = label.find_next('span', class_='text-font-normal')
        if value:
            record[label.get_text(' ', strip=True)] = value.get_text(' ', strip=True)
    supplier = next((a.get('href') for a in card.select('a[href]') if 'View more about this company' in a.get_text(' ', strip=True)), '')
    record['supplier_url'] = urljoin(DOMAIN, supplier) if supplier else ''
    return record


def browser_config() -> BrowserConfig:
    return BrowserConfig(headless=True, verbose=False, extra_args=['--disable-gpu', '--single-process'])


async def fetch_from_crawler(crawler: AsyncWebCrawler, l1: dict[str, str]) -> dict[str, str]:
    url = canonical_exhibitor_url(l1['url'])
    result = await crawler.arun(url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
    if result.status_code == 403:
        return blocked_record(l1, url, 403)
    if not result.success or result.status_code != 200:
        raise RuntimeError(f'{url}: success={result.success}, status={result.status_code}')
    return parse_detail(result.html, l1, url)


async def fetch_one(l1: dict[str, str]) -> dict[str, str]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with AsyncWebCrawler(config=browser_config()) as crawler:
                return await fetch_from_crawler(crawler, l1)
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES: await asyncio.sleep(attempt * 2)
    raise RuntimeError(f'{canonical_exhibitor_url(l1["url"])}: failed after {MAX_RETRIES} fresh-browser attempts: {last_error}')


async def extract(l1_records: list[dict[str, str]]) -> list[dict[str, str]]:
    """Use one fresh browser per three-profile batch; preserve L1 order."""
    records: list[dict[str, str]] = []
    for queue_start in range(0, len(l1_records), QUEUE_SIZE):
        queue = l1_records[queue_start:queue_start + QUEUE_SIZE]
        print(f'Queue {queue_start + 1}-{queue_start + len(queue)} of {len(l1_records)}', flush=True)
        for queue_offset in range(0, len(queue), BATCH_SIZE):
            batch_start = queue_start + queue_offset
            batch = queue[queue_offset:queue_offset + BATCH_SIZE]
            print(f'Batch {batch_start + 1}-{batch_start + len(batch)} of {len(l1_records)}', flush=True)
            async with AsyncWebCrawler(config=browser_config()) as crawler:
                for offset, l1 in enumerate(batch):
                    position = batch_start + offset + 1
                    try:
                        record = await fetch_from_crawler(crawler, l1)
                    except Exception as batch_error:
                        # A failed/reused context is never trusted: retry this profile in a
                        # separate fresh browser, while preserving its source position.
                        print(f'Batch context failed at {position}; retrying fresh: {batch_error}', flush=True)
                        record = await fetch_one(l1)
                    records.append(record)
                    print(f'Processing {position}/{len(l1_records)}: {record["l2_status"]}', flush=True)
                    if position < len(l1_records): await asyncio.sleep(REQUEST_DELAY_SECONDS)
    extracted = sum(row['l2_status'] == 'extracted' for row in records)
    blocked = sum(row['l2_status'].startswith('blocked_') for row in records)
    if len(records) != len(l1_records) or extracted + blocked != len(l1_records):
        raise ValueError(f'L2 reconciliation failed: records={len(records)}, extracted={extracted}, blocked={blocked}, L1={len(l1_records)}')
    return records


def write_artifacts(prefix: str, records: list[dict[str, str]]) -> None:
    output_dir = OUTPUT_ROOT / prefix
    json_path, csv_path = output_dir / f'hktdc_{prefix}_L2.json', output_dir / f'hktdc_{prefix}_L2.csv'
    fields = list(dict.fromkeys(key for row in records for key in row))
    json_tmp, csv_tmp = json_path.with_suffix('.json.tmp'), csv_path.with_suffix('.csv.tmp')
    with json_tmp.open('w', encoding='utf-8') as handle:
        for row in records: handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    with csv_tmp.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n'); writer.writeheader(); writer.writerows(records)
    json_tmp.replace(json_path); csv_tmp.replace(csv_path)


def main() -> None:
    prefix = input('What is the prefix of your exhibition?').strip()
    l1_path = OUTPUT_ROOT / prefix / f'hktdc_{prefix}_L1.csv'
    with l1_path.open(encoding='utf-8-sig', newline='') as handle:
        l1_records = list(csv.DictReader(handle))
    required = {'Company Name', 'Location', 'url'}
    if not l1_records or not required.issubset(l1_records[0]):
        raise ValueError(f'L1 missing required columns: {sorted(required)}')
    if any(not row['url'] for row in l1_records): raise ValueError('L1 has missing exhibitor URLs')
    records = asyncio.run(extract(l1_records))
    write_artifacts(prefix, records)
    extracted = sum(row['l2_status'] == 'extracted' for row in records)
    print(json.dumps({'records': len(records), 'extracted': extracted, 'blocked': len(records)-extracted, 'stage': 'L2'}))


if __name__ == '__main__': main()
