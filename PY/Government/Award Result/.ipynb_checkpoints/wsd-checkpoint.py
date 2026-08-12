import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re

import os

os.chdir('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/gov_cntract/Raw/data')

# =====================================================================
# 1. DEFINE SCHEMAS
# =====================================================================

# L1 Schema: Only targets the links we need to jump into
l1_css_schema = {
    "name": "L1_Link_Extractor",
    "baseSelector": "#divList table tbody tr.row",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "PWP No",
            "selector": "td:nth-child(1)",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "ref",
            "selector": "td:nth-child(1)",           # Selector for the actual L2 URL
            "type": "text"
        },
     {
            "name": "contract_url",
            "selector": "td:nth-child(3) a",           # Selector for the actual L2 URL
            "type": "attribute",
            "attribute": "href"
        },
        {
            "name": "contract_title",
            "selector": "td:nth-child(4)",           # Selector for the actual L2 URL
            "type": "text"
        }
        ,
        {
            "name": "district",
            "selector": "td:nth-child(5)",           # Selector for the actual L2 URL
            "type": "text"
        }
        ,
        {
            "name": "contract_sum",
            "selector": "td:nth-child(6)",           # Selector for the actual L2 URL
            "type": "text"
        }
        ,
        {
            "name": "award_date",
            "selector": "td:nth-child(7)",           # Selector for the actual L2 URL
            "type": "text"
        }
        ,
        {
            "name": "responsible_division",
            "selector": "td:nth-child(8)",           # Selector for the actual L2 URL
            "type": "text"
        }
    ]
}

		
# L2 Schema: Targets the deep data once we arrive at the 2nd URL
l2_css_schema = {
    "name": "L2_Deep_Data_Extractor",
    "baseSelector": "#mainContent table tbody",  # Targets field wrappers
    "fields": [
        {
            "name": "date_of_commence",
            "selector": "tr:nth-child(8)",     # Extracts "Contractor :"
            "type": "text"
        },
        {
            "name": "est_completion_date",
            "selector": "tr:nth-child(9)",     # Extracts "Contractor :"
            "type": "text"
        },
        {
            "name": "status_of_work",
            "selector": "tr:nth-child(10)",     # Extracts "Contractor :"
            "type": "text"
        }
    ]
}

# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str):
    async with AsyncWebCrawler() as crawler:
        
        # --- STAGE 1: Extract URLs from Level 1 ---
        print(f"[L1] Crawling index: {l1_start_url}")
        l1_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(l1_css_schema),
            cache_mode=True,
            magic=True,
        wait_for="css:.table, table, .content_block",  # Wait for table or content container
        delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
        js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        l1_result = await crawler.arun(url=l1_start_url, config=l1_config)
        
        if not l1_result.success or not l1_result.extracted_content:
            print("Failed to parse L1 or no URLs found.")
            return

        # Parse the JSON string out of the L1 result
        l1_data = json.loads(l1_result.extracted_content)

        #print(l1_data)
        # Flatten into a clean array of absolute URLs
        l2_urls = ['https://www.wsd.gov.hk/en/tenders-contracts-and-consultancies/contracts/active-wsd-capital-works-contracts/'+item['contract_url'] for item in l1_data if item.get('contract_url')]
        l2_pwp = [item['PWP No'] for item in l1_data if item.get('PWP No')]
        
        l2_ref = [item['ref'] for item in l1_data if item.get('ref')]
        l2_title = [item['contract_title'] for item in l1_data if item.get('contract_title')]
        l2_district = [item['district'] for item in l1_data if item.get('district')]
        l2_contract_sum = [item['contract_sum'] for item in l1_data if item.get('contract_sum')]
        l2_dt = [item['award_date'] for item in l1_data if item.get('award_date')]
        l2_responsible_division = [item['responsible_division'] for item in l1_data if item.get('responsible_division')]

        
        print(f"[L1] Discovered {len(l2_urls)} deep links to process.")
        if not l2_urls:
            return

        # --- STAGE 2: Mass Extract Data From Level 2 URLs ---
        print("[L2] Beginning batch crawl on extracted target links...")
        l2_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(l2_css_schema),
            cache_mode=True,
            delay_before_return_html=3.0,  
            wait_for="#mainContent",
            js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        
        # arun_many executes the array concurrently across your browser instances
        l2_results = await crawler.arun_many(urls=l2_urls, config=l2_config)
        
        
        # Combine the results
        final_dataset = []
        for url, res, ref, dt, pwp, title, district, contract_sum, responsible_division in zip(l2_urls, l2_results, l2_ref,l2_dt, l2_pwp, l2_title, l2_district, l2_contract_sum, l2_responsible_division):
            #print(res.extracted_content)
            if res.success: 
                parsed_page_data = json.loads(res.extracted_content)
                    
                if isinstance(parsed_page_data, list):
                    for record in parsed_page_data:
                        record['department'] = 'Water Supplies Department'
                        record['type'] = 'contract_awarded'
                        record['url'] = url
                        record['ref'] = ref
                        record['award_date'] = dt
                        record['pwp_no'] = pwp
                        record['description'] = title 
                        record['district'] = district
                        record['sum'] = contract_sum  
                        record['responsible_division'] = responsible_division

                        #print(record)

                        with open('gov_wsd.json', "a") as f:
                            #f.write(json.dumps(record, ensure_ascii=False) + '\n')
                            json.dump(record, f,indent=1, default=str,ensure_ascii=False)
                            f.write('\n')
                
        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(final_dataset, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.wsd.gov.hk/en/tenders-contracts-and-consultancies/contracts/active-wsd-capital-works-contracts/index.html"))


