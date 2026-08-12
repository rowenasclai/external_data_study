import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re

import os

os.chdir('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/gov_cntract/Raw/data')


# =====================================================================
# TSD
# 1. DEFINE SCHEMAS
# =====================================================================

# L1 Schema: Only targets the links we need to jump into

l1_css_schema = {
    "name": "L1_Link_Extractor",
    "baseSelector": "#content tr",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "ref",
            "selector": "td:nth-child(1)",           # Selector for the actual L2 URL
            "type": "text"
        },
     {
            "name": "award_date",
            "selector": "td:nth-child(2)",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "awardee",
            "selector": "td:nth-child(3)",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "sum",
            "selector": "td:nth-child(4)",           # Selector for the actual L2 URL
            "type": "text"
        }
        ,
        {
            "name": "contract_duration",
            "selector": "td:nth-child(5)",           # Selector for the actual L2 URL
            "type": "text"
        }
    ]
}



# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str, file_name):
    async with AsyncWebCrawler() as crawler:
        
        # --- STAGE 1: Extract URLs from Level 1 ---
        print(f"[L1] Crawling index: {l1_start_url}")
        l1_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(l1_css_schema),
            cache_mode=True,
            magic=True,
            wait_for="#mainContent",  # Wait for table or content container
            delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
            js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        l1_result = await crawler.arun(url=l1_start_url, config=l1_config)
        
        if not l1_result.success or not l1_result.extracted_content:
            print("Failed to parse L1 or no URLs found.")
            return

        # Parse the JSON string out of the L1 result
        l1_data = json.loads(l1_result.extracted_content)

        if isinstance(l1_data, list):
            for record in l1_data:
                record['department'] = 'Transport Department'
                record['type'] = 'contract_award'
                
                try:
                    record['description']=record['ref'][record['ref'].index('<br/><br/>'):]
                    record['ref']=record['ref'][:record['ref'].index('<br/>')]

                except:
                    pass
               
                #print(record)

                with open(file_name, "a") as f:
                    #f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    json.dump(record, f,indent=1, default=str,ensure_ascii=False)
                    f.write('\n')     
        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(final_dataset, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.wsd.gov.hk/en/tenders-contracts-and-consultancies/consultancies/award-consultancies/index.html",'gov_td.json'))

asyncio.run(run_decoupled_crawl("https://www.wsd.gov.hk/en/tenders-contracts-and-consultancies/consultancies/award-consultancies/index.html",'gov_td_consultant.json'))


