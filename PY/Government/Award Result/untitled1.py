import asyncio
import json
import os
import re
from html import unescape
from urllib.parse import urljoin
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy, CacheMode

os.chdir('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/gov_cntract/Raw/data')

# =====================================================================
# 1. DEFINE SCHEMAS
# =====================================================================

l1_css_schema = {
    "name": "L1_Link_Extractor",
    "baseSelector": "div.content ul li",
    "fields": [
        {"name": "Subject_Link", "selector": "a", "type": "attribute", "attribute": "href"},
        {"name": "l1_description", "selector": "a", "type": "text"}
    ]
}

# Use broad table row selector + explicit td:nth-child(N)
l2_css_schema = {
    "name": "L2_Deep_Data_Extractor",
    "baseSelector": "table tr",
    "fields": [
        {"name": "ref", "selector": "td:nth-child(1)", "type": "text"},
        {"name": "Tendering Procedure", "selector": "td:nth-child(2)", "type": "text"},
        {"name": "description", "selector": "td:nth-child(3)", "type": "text"},
        {"name": "Contractor(s) and Address(es)", "selector": "td:nth-child(4)", "type": "text"},
        {"name": "contractor_html", "selector": "td:nth-child(4)", "type": "html"},
        {"name": "period", "selector": "td:nth-child(5)", "type": "text"},
        {"name": "sum", "selector": "td:nth-child(6)", "type": "text"},
    ]
}


def split_contractor_and_address(raw_html: str) -> tuple[str, str]:
    """Split contractor name (first block/line) from address (remaining lines)."""
    if not raw_html:
        return "", ""
    # Normalize <br>, </p>, </div> into newlines, then strip remaining tags
    text = re.sub(r'<(?:br\s*/?|/p|/div|/li)\s*>', '\n', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    lines = [unescape(line).strip() for line in text.splitlines() if unescape(line).strip()]
    if not lines:
        return "", ""
    return lines[0], ", ".join(lines[1:])


# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str):
    async with AsyncWebCrawler() as crawler:
        print(f"[L1] Crawling index: {l1_start_url}")
        l1_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(l1_css_schema),
            cache_mode=CacheMode.BYPASS,
            wait_for="div.content",
            delay_before_return_html=2.0,
        )
        l1_result = await crawler.arun(url=l1_start_url, config=l1_config)

        if not l1_result.success or not l1_result.extracted_content:
            print("Failed to parse L1 or no URLs found.")
            return

        l1_data = json.loads(l1_result.extracted_content)

        # Keep URL and description paired; skip non-contract/archive links
        l2_items = [
            (urljoin(l1_start_url, item['Subject_Link']), item.get('l1_description', '').strip())
            for item in l1_data
            if item.get('Subject_Link') and 'awarded' in item.get('l1_description', '').lower()
        ]

        print(f"[L1] Discovered {len(l2_items)} contract links to process.")
        if not l2_items:
            return

        l2_urls = [u for u, _ in l2_items]
        l2_descs = [d for _, d in l2_items]

        l2_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(l2_css_schema),
            cache_mode=CacheMode.BYPASS,
            wait_for="table",
            delay_before_return_html=2.0,
        )
        l2_results = await crawler.arun_many(urls=l2_urls, config=l2_config)

        with open('gov_epd.json', "w", encoding="utf-8") as f:
            for url, res, desc in zip(l2_urls, l2_results, l2_descs):
                if not (res.success and res.extracted_content):
                    print(f"[WARN] Failed or empty: {url}")
                    continue

                parsed_rows = json.loads(res.extracted_content)
                for record in parsed_rows:
                    ref = (record.get('ref') or '').strip()
                    # Skip header rows or empty layout rows
                    if not ref or ref.lower().startswith('tender reference'):
                        continue

                    awardee, address = split_contractor_and_address(record.pop('contractor_html', ''))
                    record['awardee'] = awardee
                    record['Contractor Address(es)'] = address
                    record['department'] = 'Environmental Protection Department'
                    record['type'] = 'contract_awarded'
                    record['url'] = url

                    match = re.search(r'Awarded in\s+([^)]+)', desc, flags=re.IGNORECASE)
                    record['award_date'] = match.group(1).strip() if match else desc

                    f.write(json.dumps(record, ensure_ascii=False) + '\n')


asyncio.run(run_decoupled_crawl("https://www.epd.gov.hk/epd/english/news_events/notices/notices.html"))