"""Extract public HKTDC exhibitor-list cards with Crawl4AI in headless mode."""
from __future__ import annotations

import asyncio
import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / 'Result' / 'Exhibition Organizers' / 'HKTDC'
PAGE_SIZE = 50
MAX_RETRIES = 2
STATUS_RE = re.compile(r'^Shown\s+(\d+)-(\d+)\s+of\s+Total Result\s+(\d+)$')
FIELDS = ['Company Name', 'Location', 'Booth', 'url']


def page_url(prefix: str, page_number: int) -> str:
    return (
        f'https://www.hktdc.com/event/{prefix}/en/exhibitor-list'
        f'?pageNum={page_number}&pageSize={PAGE_SIZE}'
    )


def parse_page(html: str, page_number: int, expected_total: int | None = None) -> tuple[int, list[dict[str, str]]]:
    soup = BeautifulSoup(html, 'html.parser')
    statuses = [node.get_text(' ', strip=True) for node in soup.select('.vep-exhibitor-result-status span')]
    count_text = next((text for text in statuses if STATUS_RE.fullmatch(text)), None)
    if not count_text:
        raise ValueError(f'page {page_number}: public result-count status was not found')
    _, _, total_text = STATUS_RE.fullmatch(count_text).groups()
    total = int(total_text)
    if expected_total is not None and total != expected_total:
        raise ValueError(f'page {page_number}: total changed from {expected_total} to {total}')

    records = []
    for position, card in enumerate(soup.select('.d-flex.flex-column.vep-p-4'), start=1):
        # Crawl4AI returns the whole DOM, including hidden bookmark-modal text.
        # Select the published card fields explicitly rather than card.get_text().
        company = card.select_one('span.text-level-subtitle.text-font-bold')
        location = card.select_one('span.text-decoration-underline')
        booth = card.select_one('span[class*="exhibitors_formatDtl"]')
        if not company or not location:
            raise ValueError(f'page {page_number}, card {position}: missing company or location')
        company_link = company.find_parent('a', href=True)
        records.append({
            'Company Name': company.get_text(' ', strip=True),
            'Location': location.get_text(' ', strip=True),
            'Booth': booth.get_text(' ', strip=True) if booth else '',
            'url': urljoin('https://www.hktdc.com', company_link['href']) if company_link else '',
        })
    if not records:
        raise ValueError(f'page {page_number}: no exhibitor cards')
    return total, records


def browser_config() -> BrowserConfig:
    return BrowserConfig(
        headless=True,
        verbose=False,
        # A fresh single-process browser is used for each bounded page batch.
        extra_args=['--disable-gpu', '--single-process'],
    )


async def fetch_page(prefix: str, page_number: int, expected_total: int | None) -> tuple[int, list[dict[str, str]]]:
    """Fetch one page in its own browser process; never reuse a crashed context."""
    url = page_url(prefix, page_number)
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with AsyncWebCrawler(config=browser_config()) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(
                        wait_for='css:.vep-exhibitor-result-status span',
                        cache_mode=CacheMode.BYPASS,
                    ),
                )
            if not result.success or result.status_code != 200:
                raise RuntimeError(f'HTTP/status failure: success={result.success}, status={result.status_code}')
            return parse_page(result.html, page_number, expected_total)
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                await asyncio.sleep(attempt * 2)
    raise RuntimeError(f'page {page_number} failed after {MAX_RETRIES} fresh-browser attempts: {last_error}')


async def extract(prefix: str) -> list[dict[str, str]]:
    total, records = await fetch_page(prefix, 1, None)
    print(f'Processing 1-{min(PAGE_SIZE, total)} out of {total}', flush=True)
    page_count = (total + PAGE_SIZE - 1) // PAGE_SIZE
    if page_count > 1:
        await asyncio.sleep(3)  # conservative delay between public page requests
    for page_number in range(2, page_count + 1):
        _, page_records = await fetch_page(prefix, page_number, total)
        expected = min(PAGE_SIZE, total - (page_number - 1) * PAGE_SIZE)
        if len(page_records) != expected:
            raise ValueError(f'page {page_number}: expected {expected} cards, parsed {len(page_records)}')
        records.extend(page_records)
        print(f'Processing {(page_number - 1) * PAGE_SIZE + 1}-{min(page_number * PAGE_SIZE, total)} out of {total}', flush=True)
        if page_number < page_count:
            await asyncio.sleep(3)  # conservative delay between public page requests
    if len(records) != total:
        raise ValueError(f'expected {total} exhibitors, parsed {len(records)}')
    if any(not record['Company Name'] for record in records):
        raise ValueError('one or more records have a blank company name')
    return records


def write_artifacts(prefix: str, records: list[dict[str, str]]) -> None:
    output_dir = OUTPUT_ROOT / prefix
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f'hktdc_{prefix}_L1.json'
    csv_path = output_dir / f'hktdc_{prefix}_L1.csv'
    temporary_json = json_path.with_suffix('.json.tmp')
    temporary_csv = csv_path.with_suffix('.csv.tmp')
    with temporary_json.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')
    with temporary_csv.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)
    temporary_json.replace(json_path)
    temporary_csv.replace(csv_path)
    print(json.dumps({'records': len(records), 'json': str(json_path), 'csv': str(csv_path)}))


def main() -> None:
    prefix = input('What is the prefix of your exhibition?').strip()
    if not prefix:
        raise ValueError('an exhibition prefix is required')
    write_artifacts(prefix, asyncio.run(extract(prefix)))


if __name__ == '__main__':
    main()
