# =====================================================================
# EPD Contract Extraction
# =====================================================================

import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re

# =====================================================================
# 1. DEFINE SCHEMAS
# =====================================================================

# L1 Schema: Only targets the links we need to jump into
l1_css_schema = {
    "name": "L1_Link_Extractor",
    "baseSelector": "div.content ul li",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "Subject_Link",
            "selector": "a",           # Selector for the actual L2 URL
            "type": "attribute",
            "attribute": "href"
        },
     {
            "name": "Subject",
            "selector": "td:nth-child(2) a",           # Selector for the actual L2 URL
            "type": "text"
        }
    ]
}

		
# L2 Schema: Targets the deep data once we arrive at the 2nd URL
l2_css_schema = {
    "name": "L2_Deep_Data_Extractor",
    "baseSelector": "div.content table tbody tr",  # Targets field wrappers
    "fields": [
        {
            "name": "Tender Reference",
            "selector": "td:nth-child(1) p",     # Extracts "Contractor :"
            "type": "text"
        },
        {
            "name": "Tendering Procedure",
            "selector": "td:nth-child(2) p",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "Subject",
            "selector": "td:nth-child(3) p",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "Contractor(s) and Address(es)",
            "selector": "td:nth-child(4) p",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "Contractor(s)",
            "selector": "td:nth-child(4) p",       # Extracts ALL text inside <li> including value
            #"type": "text"
            "type": "regex",
            "regex": "<p>([^<]+?)*<br/>\\n" # Captures text right before a break/newline
        },
        {
            "name": "Contractor Address(es)",
            "selector": "td:nth-child(4) p br:nth-child(2),td:nth-child(4) p:nth-child(2)",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "Awarded Period",
            "selector": "td:nth-child(5) p",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "Estimated Awarded Sum",
            "selector": "td:nth-child(6) p",       # Extracts ALL text inside <li> including value
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
        wait_for="div.content",  # Wait for table or content container
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
        l2_urls = ['https://www.epd.gov.hk/epd/english/news_events/notices/'+item['Subject_Link'] for item in l1_data if item.get('Subject_Link')]
        
        
        print(f"[L1] Discovered {len(l2_urls)} deep links to process.")
        if not l2_urls:
            return

        # --- STAGE 2: Mass Extract Data From Level 2 URLs ---
        print("[L2] Beginning batch crawl on extracted target links...")
        l2_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(l2_css_schema),
            cache_mode=True,
            delay_before_return_html=3.0,  
            wait_for="div.content",
            js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        
        # arun_many executes the array concurrently across your browser instances
        l2_results = await crawler.arun_many(urls=l2_urls, config=l2_config)
        
        
        # Combine the results
        final_dataset = []
        for url, res in zip(l2_urls, l2_results):
            if res.success and res.extracted_content:
                parsed_page_data = json.loads(res.extracted_content)


                if isinstance(parsed_page_data, list):
                    for record in parsed_page_data:
                        record['department'] = 'epd'
                        record['type'] = 'contract_awarded'
                        record['url'] = url

                        try:
                            record['Contractor(s)']=record['Contractor(s)'][record['Contractor(s)'].index('<p>')+3:record['Contractor(s)'].index('<br/>')]

                        except:
                            record['Contractor(s)']=record['Contractor(s)'][record['Contractor(s)'].index('<p>')+3:record['Contractor(s)'].index('</p>')]  

                    with open('gov_epd.json', "a") as f:
                
                # 2. Dump individual record dictionary as a single JSON line
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        #print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(final_dataset, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.epd.gov.hk/epd/english/news_events/notices/notices.html"))


