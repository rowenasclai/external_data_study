import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, JsonCssExtractionStrategy

import os

from pathlib import Path

RUN_DATA_DIR = Path(os.environ["GOV_HERMES_DATA_DIR"]).resolve()
RUN_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.chdir(RUN_DATA_DIR)

async def main():
    # 1. Configure browser to handle potential firewall restrictions and preserve HTML structure
    browser_config = BrowserConfig(headless=True)

    # 2. Define schema to map each .table_wrapper as a distinct record
    hyd_schema = {
        "name": "HYD Records Extractor",
        "baseSelector": "#content tbody tr", 
        "fields": [
            {"name": "ref", "selector": "td:nth-child(1)", "type": "text"},
            {"name": "description", "selector": "td:nth-child(2)", "type": "text"},
            {"name": "award_date", "selector": "td:nth-child(3)", "type": "text"},
            {"name": "awardee", "selector": "td:nth-child(4)", "type": "text"},
            {"name": "type", "selector": "td:nth-child(5)", "type": "text"},
            {"name": "sum", "selector": "td:nth-child(6)", "type": "text"}
        ]
    }

    
    # 3. Apply configurations to extract data
    run_config = CrawlerRunConfig(
        word_count_threshold=0, 
        extraction_strategy=JsonCssExtractionStrategy(schema=hyd_schema),
        magic=True,
        wait_for="#content",  # Wait for table or content container
        delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
        js_code="window.scrollTo(0, document.body.scrollHeight);"
    )
    

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result_contract = await crawler.arun(
            url="https://www.hyd.gov.hk/en/tender_notices/contracts/awarded/index.html",
            config=run_config
        )
        result_consultant = await crawler.arun(
            url="https://www.hyd.gov.hk/en/tender_notices/consultancies/awarded/index.html",
            config=run_config
        )

        #results = await crawler.arun_many(urls=urls, configs=run_configs)

        #print(results.success)

        for result in result_contract:
            if result.success:
                try:
                    data = json.loads(result.extracted_content)
                    #print(data)
                    #print(result.extracted_content)
                    if isinstance(data, list):
                        for record in data:
                            record['department'] = 'Highways Department'

                        #print(record)
                            with open('gov_hyd.json', "a") as f:
                                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                            #json.dump(record, f,indent=1, default=str,ensure_ascii=False)

                except:
                    print("Fail to parse")

        for result in result_consultant:
            if result.success and result.extracted_content:
                try:
                    data = json.loads(result.extracted_content)
                    #print(data)
                    #print(result.extracted_content)
                    if isinstance(data, list):
                        for record in data:
                            record['department'] = 'hyd'

                        #print(record)
                            with open('gov_hyd.json', "a") as f:
                                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                            #json.dump(record, f,indent=1, default=str,ensure_ascii=False)

                except:
                    print("Fail to parse")
                    
                    
                #print(type(result.extracted_content))
                #data = json.loads(result.extracted_content)
            #data['department']='emsd'

                # if isinstance(data, list):
                #     for record in data:
                #         record['department'] = 'hyd'

                #         with open('gov_hyd.json', "a") as f:
                #             json.dump(record, f,indent=1, default=str,ensure_ascii=False)
                
                # 2. Dump individual record dictionary as a single JSON line
                            #f.write(json.dumps(record, ensure_ascii=False) + '\n')

            
            else:
                print(f"Extraction failed: {result.error_message}")

        

if __name__ == "__main__":
    asyncio.run(main())
