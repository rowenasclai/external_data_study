import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re
import os

# =====================================================================
# 1. DEFINE SCHEMAS
# =====================================================================

os.chdir('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/gov_cntract/Raw/data')

# L1 Schema: Only targets the links we need to jump into
l1_css_schema = {
    "name": "L1_Link_Extractor",
    "baseSelector": "#content table tbody tr",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "Tender Reference",
            "selector": "td:nth-child(1)",           # Selector for the actual L2 URL
            "type": "text"
        },
     {
            "name": "Subject",
            "selector": "td:nth-child(2) a",           # Selector for the actual L2 URL
            "type": "attribute",
            "attribute": "href"
        },
        {
            "name": "Awarded Date",
            "selector": "td:nth-child(3)",           # Selector for the actual L2 URL
            "type": "text"
        }
    ]
}

		
# L2 Schema: Targets the deep data once we arrive at the 2nd URL
l2_css_schema = {
    "name": "L2_Deep_Data_Extractor",
    "baseSelector": "#content",  # Targets field wrappers
    "fields": [
        {
            "name": "label",
            "selector": "h3:nth-child(5)",     # Extracts "Contractor :"
            "type": "text"
        },
        {
            "name": "full_text",
            "selector": "",       # Extracts ALL text inside <li> including value
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
        l2_urls = ['https://www.cedd.gov.hk/'+item['Subject'] for item in l1_data if item.get('Subject')]
        l2_ref = [item['Tender Reference'] for item in l1_data if item.get('Tender Reference')]
        l2_dt = [item['Awarded Date'] for item in l1_data if item.get('Awarded Date')]
        
        
        print(f"[L1] Discovered {len(l2_urls)} deep links to process.")
        if not l2_urls:
            return

        # --- STAGE 2: Mass Extract Data From Level 2 URLs ---
        print("[L2] Beginning batch crawl on extracted target links...")
        l2_config = CrawlerRunConfig(
            #extraction_strategy=JsonCssExtractionStrategy(l2_css_schema),
            cache_mode=True,
            delay_before_return_html=3.0,  
            wait_for="#content",
            js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        
        # arun_many executes the array concurrently across your browser instances
        l2_results = await crawler.arun_many(urls=l2_urls, config=l2_config)
        
        
        # Combine the results
        final_dataset = []
        for url, res, ref, dt in zip(l2_urls, l2_results, l2_ref,l2_dt):
            if res.success : #and res.extracted_content:
                #parsed_page_data = json.loads(res.extracted_content)
                #items = parsed_page_data
                #record = {"contractor_name": "N/A", "contractor_address": "N/A", "awarded_sum": "N/A"}
                #print(res.markdown)
                #res.markdown

                raw_lines_list = [line.strip() for line in res.markdown.split('\n') if line.strip()]
                #print(raw_lines_list[raw_lines_list.index("### Contractor :")+1])

                # Inject the source URL so you know where this specific data came from
                record={
                    "department": "Civil Engineering and Development Department", "type": "contract_awarded",
                    "ref":ref,
                    "url": url,
                    #"extracted_data": parsed_page_data              
                    "description":raw_lines_list[raw_lines_list.index("### Subject :")+1],
                    "awardee":raw_lines_list[raw_lines_list.index("### Contractor :")+1],
                    "contractor_address":raw_lines_list[raw_lines_list.index("### Contractor's Address :")+1],
                    "quantity":raw_lines_list[raw_lines_list.index("### Quantity :")+1],
                    "award":raw_lines_list[raw_lines_list.index("### Awarded Sum (million) :")+1],
                    "award_date":dt
                }

                with open('gov_cedd.json', "a") as f:
                
                # 2. Dump individual record dictionary as a single JSON line
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print("\n=== FINAL EXTRACTED DATA ===")
        print(json.dumps(final_dataset, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.cedd.gov.hk/eng/tender-notices/contracts/contracts-awarded/index.html"))


