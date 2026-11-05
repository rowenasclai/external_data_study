import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import os

os.chdir('/Users/rowena/Other Projects/external_data_study/Result/')

async def main():
    # 1. Configure browser to handle potential firewall restrictions and preserve HTML structure
    #browser_config = BrowserConfig(headless=True, text_mode=False)
    browser_cfg = BrowserConfig(
        # browser_type="chromium",
        browser_type="chromium",
        cdp_url="http://localhost:9222"
        # headless=False,                # Must be False to pass Turnstile challenge
        # enable_stealth=True,           # Masks navigator.webdriver and fingerprint
        # use_persistent_context=True#,   # Saves cf_clearance cookie across runs
        # user_data_dir="./importinfo_profile",
        # args=[
        #     "--disable-blink-features=AutomationControlled",
        #     "--no-sandbox"
        # ]
    )

#Company Name	Location	Total Records	Records Last 90 Days	Records Last 30 Days	Most Recent Record
    
    # 2. Define schema to map each .table_wrapper as a distinct record
    schema = {
        "name": "All Shipment",
        "baseSelector": "table.table-striped tbody tr", 
        "fields": [
            {"name": "Company_Name", "selector": "td:nth-child(1) a", "type": "text"},
            {"name": "Location", "selector": "td:nth-child(2)", "type": "text"},
            #{"name": "document_url", "selector": "tr:nth-child(2) td a", "type": "attribute", "attribute": "href"},
            {"name": "Total_Records", "selector": "td:nth-child(3)", "type": "text"},
            {"name": "Records_L90D", "selector": "td:nth-child(4)", "type": "text"},
            {"name": "Records_L30D", "selector": "td:nth-child(5)", "type": "text"},
            {"name": "Most_Recent_Shipment", "selector": "td:nth-child(6)", "type": "text"}
        ]
    }

    
    # 3. Apply configurations to extract data
    # run_config = CrawlerRunConfig(
    #     word_count_threshold=0, 
    #     #content_filter=None, 
    #     extraction_strategy=JsonCssExtractionStrategy(schema=emsd_schema),
    #     magic=True,
    #     #wait_for="css:.table, table, .content_block",  # Wait for table or content container
    #     #wait_for="div#sa-divider",
    #     delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
    #     #js_code="window.scrollTo(0, document.body.scrollHeight);"
    # )

    extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)

    run_config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(schema),
        magic=True,                    # Crawl4AI anti-detection & human simulation
        simulate_user=True,            # Simulates mouse movements & scrolling
        override_navigator=True,
        wait_for="css:table.table-striped tbody tr",
        wait_for_timeout=60000,        # Give yourself 60s on first run if manual click is needed
        cache_mode=CacheMode.BYPASS
    )

    for i in range(1353,2290):
    
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(
                url="https://www.importinfo.com/companies?page="+str(i),
                config=run_config
            )
        
            if result.success:
                data = json.loads(result.extracted_content)
                #print(data)
            #data['department']='emsd'

                if isinstance(data, list):
                    for record in data:
                    # record['department'] = 'Civil Engineering and Development Department'
                    # record['type'] = 'consultancy'
                    # record['url']='https://www.cedd.gov.hk/eng/tender-notices/consultancy-agreements/consultancies-awarded/index.html'

                        with open('all_Shipments.json', "a") as f:
                
                # 2. Dump individual record dictionary as a single JSON line
                            f.write(json.dumps(record, ensure_ascii=False) + '\n')

            
            else:
                print(f"Extraction failed: {result.error_message}")

        

if __name__ == "__main__":
    asyncio.run(main())
