import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re


import os

from pathlib import Path

RUN_DATA_DIR = Path(os.environ["GOV_HERMES_DATA_DIR"]).resolve()
RUN_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.chdir(RUN_DATA_DIR)

# =====================================================================
# 1. DEFINE SCHEMAS
# =====================================================================

# L1 Schema: Only targets the links we need to jump into

L1_schema = {
    "name": "Tender Notices Extractor",
    # Target each individual repeating data row container
    "baseSelector": "div.resultDataContainerBox div.data",
    "fields": [
        {
            "name": "type",
            "selector": "div.typeData",
            "type": "text"
        },
        {
            "name": "contract_ref",
            "selector": "div.contractData",
            "type": "text"
        },
        {
            "name": "title",
            "selector": "div.titleData a", # Grabs text inside the anchor link
            "type": "text"
        },
        {
            "name": "link",
            "selector": "div.titleData a", # Grabs the actual URL path
            "type": "attribute",
            "attribute": "href"
        },
        {
            "name": "publish_date",
            "selector": "div.closingDateData",
            "type": "text"
        }
    ]
}

L2_schema = {
    "name": "Tender Notices Details Extractor",
    # Target each individual repeating data row container
    "baseSelector": "div.contentContainer",
    "fields": [
        {
            "name": "title",
            "selector": "div.componentTitle",
            "type": "text"
        },
        {
            "name": "paragraph 1",
            "selector": "p",
            "type": "text"
        },
        {
            "name": "paragraph 2",
            "selector": "p::nth-child(2)", # Grabs text inside the anchor link
            "type": "text"
        }
    ]
}

#strategy = JsonCssExtractionStrategy(schema=schema)


# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str):
    async with AsyncWebCrawler() as crawler:
        
        # --- STAGE 1: Extract URLs from Level 1 ---
        print(f"[L1] Crawling index: {l1_start_url}")
        l1_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(L1_schema),
            cache_mode=True,
            magic=True,
        wait_for="div.resultDataContainerBox",  # Wait for table or content container
        delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
        js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        l1_result = await crawler.arun(url=l1_start_url, config=l1_config)
        
        if not l1_result.success or not l1_result.extracted_content:
            print("Failed to parse L1 or no URLs found.")
            return

        # Parse the JSON string out of the L1 result
        l1_data = json.loads(l1_result.extracted_content)

        l2_urls = ['https://www.hongkongairport.com'+item['link'] for item in l1_data if item.get('link')]
        l2_ref = [item['contract_ref'] for item in l1_data if item.get('contract_ref')]
        l2_dt = [item['publish_date'] for item in l1_data if item.get('publish_date')]
        l2_title = [item['title'] for item in l1_data if item.get('title')]
        l2_type = [item['type'] for item in l1_data if item.get('type')]
        
        
        print(f"[L1] Discovered {len(l2_urls)} deep links to process.")
        if not l2_urls:
            return

        print("[L2] Beginning batch crawl on extracted target links...")
        l2_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(L2_schema),
            cache_mode=True,
            delay_before_return_html=3.0,  
            wait_for="div.iw_section",
            js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        
        # arun_many executes the array concurrently across your browser instances
        l2_results = await crawler.arun_many(urls=l2_urls, config=l2_config)
        
        # Preserve exact unstructured source evidence for the separate
        # Hermes-authored normalization stage. No local LLM is required.
        for url, res, ref, dt, title, type1, l_data in zip(l2_urls, l2_results, l2_ref,l2_dt,l2_title,l2_type, l1_data):
            if res.success:
                raw_record = {
                    "source": "hkaa",
                    "ref": ref,
                    "publish_date": dt,
                    "description": title.replace('\n', ' ').replace('  ', ' '),
                    "type": type1,
                    "url": url,
                    "l1": l_data,
                    "extracted_content": res.extracted_content,
                    "markdown": res.markdown,
                }
                with open('gov_hkaa_unstructured.json', "a", encoding='utf-8') as f:
                    f.write(json.dumps(raw_record, ensure_ascii=False) + '\n')

        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(l1_data, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.hongkongairport.com/en/airport-authority/tender-notices/notice-of-contract-award.page"))


