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
    browser_config = BrowserConfig(headless=True, text_mode=False)

    # 2. Define schema to map each .table_wrapper as a distinct record
    emsd_schema = {
        "name": "CEDD Consultancy Records Extractor",
        "baseSelector": "div#content tbody tr", 
        "fields": [
            {"name": "ref", "selector": "td:nth-child(1)", "type": "text"},
            {"name": "description", "selector": "td:nth-child(2)", "type": "text"},
            #{"name": "document_url", "selector": "tr:nth-child(2) td a", "type": "attribute", "attribute": "href"},
            {"name": "awardee", "selector": "td:nth-child(3)", "type": "text"},
            {"name": "award_date", "selector": "td:nth-child(4)", "type": "text"},
            {"name": "start", "selector": "td:nth-child(5)", "type": "text"},
            {"name": "end", "selector": "td:nth-child(6)", "type": "text"},
            {"name": "sum", "selector": "td:nth-child(7)", "type": "text"}
        ]
    }

    
    # 3. Apply configurations to extract data
    run_config = CrawlerRunConfig(
        word_count_threshold=0, 
        #content_filter=None, 
        extraction_strategy=JsonCssExtractionStrategy(schema=emsd_schema),
        magic=True,
        #wait_for="css:.table, table, .content_block",  # Wait for table or content container
        wait_for="div#mainContent",
        delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
        js_code="window.scrollTo(0, document.body.scrollHeight);"
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://www.cedd.gov.hk/eng/tender-notices/consultancy-agreements/consultancies-awarded/index.html",
            config=run_config
        )
        
        if result.success:
            data = json.loads(result.extracted_content)
            #data['department']='emsd'

            if isinstance(data, list):
                for record in data:
                    record['department'] = 'Civil Engineering and Development Department'
                    record['type'] = 'consultancy'
                    record['url']='https://www.cedd.gov.hk/eng/tender-notices/consultancy-agreements/consultancies-awarded/index.html'

                    with open('gov_cedd_consultant.json', "a") as f:
                
                # 2. Dump individual record dictionary as a single JSON line
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')

            
        else:
            print(f"Extraction failed: {result.error_message}")

        

if __name__ == "__main__":
    asyncio.run(main())
