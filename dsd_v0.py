import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re

# =====================================================================
# DSD 1. DEFINE SCHEMAS
# =====================================================================

# L1 Schema: Only targets the links we need to jump into
l1_css_schema = {
    "name": "L1_Link_Extractor",
    "baseSelector": "div.content table tbody tr",  # Selector for your L1 grid/table rows
    "fields": [
        
     {
            "name": "Subject",
            "selector": "td:nth-child(1) a",           # Selector for the actual L2 URL
            "type": "attribute",
            "attribute": "href"
        },
        {
            "name": "type",
            "selector": "td:nth-child(2)",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "ref",
            "selector": "td:nth-child(3)",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "award_date",
            "selector": "td:nth-child(4)",           # Selector for the actual L2 URL
            "type": "text"
        }
    ]
}

		
# L2 Schema: Targets the deep data once we arrive at the 2nd URL
l2_css_schema = {
    "name": "L2_Deep_Data_Extractor",
    "baseSelector": "div.content",  # Targets field wrappers
    "fields": [
        {
            "name": "award_date",
            "selector": "div.row:nth-of-type(1) > div:nth-of-type(2)",     # Extracts "Contractor :"
            "type": "text"
        },
        {
            "name": "Contractor",
            "selector": "div.row:nth-of-type(2) > div:nth-of-type(2)",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "date_of_commence",
            "selector": "div.row:nth-of-type(3) > div:nth-of-type(2)",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "est_date_of_completion",
            "selector": "div.row:nth-of-type(4) > div:nth-of-type(2)",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "contract_sum",
            "selector": "div.row:nth-of-type(5) > div:nth-of-type(2)",       # Extracts ALL text inside <li> including value
            "type": "text"
        },
        {
            "name": "project_office",
            "selector": "div.row:nth-of-type(6) > div:nth-of-type(2)",       # Extracts ALL text inside <li> including value
            "type": "text"
        }
    ]
}

# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str):
    async with AsyncWebCrawler() as crawler:
        session_id = "pagination_scraping_session"
    
    # 2. JavaScript script designed to locate and trigger the next button
        js_click_next = """
    (() => {
        const currentBtn = document.querySelector('a.paginate_button.current');
        if (!currentBtn) return false;
        
        const nextNum = parseInt(currentBtn.textContent.trim(), 10) + 1;
        const nextBtn = Array.from(document.querySelectorAll('a.paginate_button'))
                             .find(el => parseInt(el.textContent.trim(), 10) === nextNum);
        
        if (nextBtn) {
            nextBtn.click();
            return true;
        }
        return false;
    })();
    """
        
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
        l2_urls = ['https://www.dsd.gov.hk/EN/Our_Projects/Contracts_Consultancies_Awarded/'+item['Subject'] for item in l1_data if item.get('Subject')]
        l2_type = [item['type'] for item in l1_data if item.get('type')]
        l2_ref = [item['ref'] for item in l1_data if item.get('ref')]
        l2_dt = [item['award_date'] for item in l1_data if item.get('award_date')]
        
        
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
        for url, res, ref, dt, type1 in zip(l2_urls, l2_results, l2_ref,l2_dt, l2_type):
            if res.success and res.extracted_content:
                parsed_page_data = json.loads(res.extracted_content)
                
                if isinstance(parsed_page_data, list):
                    for record in parsed_page_data:
                        record['department'] = 'dsd'
                        record['type'] = type1
                        record['url'] = url
                        record['ref'] = ref

                    with open('gov_dsd.json', "a") as f:
                
                # 2. Dump individual record dictionary as a single JSON line
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')

        
        print("\n=== FINAL EXTRACTED DATA ===")
        print(json.dumps(final_dataset, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.dsd.gov.hk/EN/Our_Projects/Contracts_Consultancies_Awarded/index.html"))


