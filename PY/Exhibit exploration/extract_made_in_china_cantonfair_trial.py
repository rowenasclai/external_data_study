#!/usr/bin/env python3
"""Public Made-in-China supplier-profile enrichment with identity-bound checkpoints.

The historical filename is retained for compatibility; callers supply the actual source
list and an explicit output stem.
"""
import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

SEARCH_URL = ('https://www.made-in-china.com/companysearch.do?subaction=hunt&style=b'
              '&mode=and&code=0&comProvince=nolimit&order=0&isOpenCorrection=1'
              '&searchType=1&word=')
FIELDS = [
    'source_position', 'input_company_name', 'search_url', 'supplier_profile_url',
    'resolved_profile_url', 'resolved_company_name', 'extraction_status',
    'status_detail', 'home_company_profile', 'about_company_profile',
    'about_general_information', 'about_trade_capacity', 'about_company_show',
    'business_performance_overall_ratings', 'source_url'
]

def text(node):
    return re.sub(r'\s+', ' ', node.get_text(' ', strip=True)) if node else ''

def norm(value):
    return re.sub(r'[^a-z0-9]+', '', (value or '').casefold())

def scalar_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def pairs(soup, item_selector, label_selector, value_selector):
    result = {}
    for item in soup.select(item_selector):
        key = text(item.select_one(label_selector)).rstrip(':')
        value = text(item.select_one(value_selector))
        if key and value:
            result[key] = value
    return result

def exact_links(soup, company):
    matches = []
    for link in soup.select('a[href]'):
        if norm(text(link)) == norm(company):
            href = urljoin('https://www.made-in-china.com', link['href'])
            if 'made-in-china.com' in href:
                matches.append(href)
    return list(dict.fromkeys(matches))

def profile_sections(html):
    soup = BeautifulSoup(html, 'html.parser')
    name = text(soup.select_one('.com-name h1'))
    home = pairs(soup, '.com-info-wp .item, .info-detal .item', '.label', '.info')
    about = {}
    headings = [text(x) for x in soup.select('.desc-title .tit h2')]
    details = soup.select('.desc > .detail')
    for heading, detail in zip(headings, details):
        value = text(detail.select_one('.desc-detail')) or text(detail)
        if value:
            about[heading] = value
    general = pairs(soup, '.info-detal .item', '.label', '.info')
    trade = pairs(soup, '.sr-comProfile-item', '.sr-comProfile-label', '.sr-comProfile-fields')
    show = [urljoin('https:', img.get('data-original') or img.get('src')) for img in soup.select('.company-show img, .com-show img, .J-show-license-photo') if (img.get('data-original') or img.get('src'))]
    ratings_box = soup.select_one('.J-review-box.overview-scores')
    ratings = text(ratings_box) if ratings_box else ''
    return name, home, about, general, trade, show, ratings

def validate(rows):
    positions = [int(row['source_position']) for row in rows]
    if positions != list(range(1, len(rows) + 1)):
        raise ValueError('source positions are not contiguous')
    if any(not row['input_company_name'] for row in rows):
        raise ValueError('blank input company name')

def write_outputs(rows, output_dir, output_stem):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f'{output_stem}.csv'
    json_path = output_dir / f'{output_stem}.json'
    with csv_path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with csv_path.open(encoding='utf-8-sig', newline='') as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(json_path.read_text(encoding='utf-8'))
    if csv_rows != [{key: str(value) for key, value in row.items()} for row in json_rows]:
        raise ValueError('CSV/JSON equivalence failed')
    return csv_path, json_path


def read_checkpoint(path, source_rows):
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
    positions = [int(record['source_position']) for record in records]
    if positions != list(range(1, len(records) + 1)):
        raise ValueError('checkpoint source positions are not contiguous')
    for record, source in zip(records, source_rows):
        if record['input_company_name'] != source['company_name'].strip():
            raise ValueError('checkpoint input identity differs from current source row')
    return records


def append_checkpoint(path, record):
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--output-stem', default='made_in_china_cantonfair_oct2026_first50_preview')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--delay', type=float, default=0.5)
    parser.add_argument('--checkpoint', help='JSONL checkpoint; defaults below the output directory')
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error('--limit must be positive')
    with Path(args.input).open(encoding='utf-8-sig', newline='') as handle:
        source_rows = []
        for row in csv.DictReader(handle):
            if len(source_rows) == args.limit: break
            source_rows.append(row)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = Path(args.checkpoint) if args.checkpoint else output_dir / f'{args.output_stem}.checkpoint.jsonl'
    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0 (compatible; public-directory-research/1.0)'
    output = read_checkpoint(checkpoint_path, source_rows)
    for position, source in enumerate(source_rows[len(output):], len(output) + 1):
        company = source['company_name'].strip()
        search_url = SEARCH_URL + quote(company)
        record = {key: '' for key in FIELDS}
        record.update({'source_position': str(position), 'input_company_name': company, 'search_url': search_url, 'source_url': search_url})
        try:
            response = session.get(search_url, timeout=(15, 60))
            response.raise_for_status()
            candidates = exact_links(BeautifulSoup(response.text, 'html.parser'), company)
            if not candidates:
                record.update(extraction_status='no_exact_supplier_match', status_detail='No exact normalized supplier-name link displayed by the public search result.')
            elif len(candidates) > 1:
                record.update(extraction_status='ambiguous_exact_supplier_match', status_detail='More than one exact normalized supplier-name link displayed; no profile attributed.', supplier_profile_url=scalar_json(candidates))
            else:
                profile_url = candidates[0]
                record['supplier_profile_url'] = profile_url
                profile = session.get(profile_url, timeout=(15, 60))
                profile.raise_for_status()
                resolved_name, home, about, general, trade, show, ratings = profile_sections(profile.text)
                if norm(resolved_name) != norm(company):
                    record.update(extraction_status='identity_mismatch', status_detail='Redirected profile company name does not exactly match the source company name.', resolved_profile_url=profile.url, resolved_company_name=resolved_name)
                else:
                    record.update(extraction_status='extracted', status_detail='Public profile identity matched.', resolved_profile_url=profile.url, resolved_company_name=resolved_name, home_company_profile=scalar_json(home) if home else 'source_omitted', about_company_profile=scalar_json(about) if about else 'source_omitted', about_general_information=scalar_json(general) if general else 'source_omitted', about_trade_capacity=scalar_json(trade) if trade else 'source_omitted', about_company_show=scalar_json(show) if show else 'source_omitted', business_performance_overall_ratings=ratings or 'source_omitted', source_url=profile.url)
        except requests.RequestException as exc:
            record.update(extraction_status='request_error', status_detail=type(exc).__name__ + ': ' + str(exc)[:180])
        output.append(record)
        append_checkpoint(checkpoint_path, record)
        time.sleep(args.delay)
    validate(output)
    csv_path, json_path = write_outputs(output, output_dir, args.output_stem)
    counts = {}
    for row in output: counts[row['extraction_status']] = counts.get(row['extraction_status'], 0) + 1
    print(json.dumps({'records': len(output), 'outcomes': counts, 'csv': str(csv_path), 'json': str(json_path)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
