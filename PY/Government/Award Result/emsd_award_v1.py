import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, JsonCssExtractionStrategy

async def main():
    # 1. Configure browser to handle potential firewall restrictions and preserve HTML structure
    browser_config = BrowserConfig(headless=True, text_mode=False)

    # 2. Define schema to map each .table_wrapper as a distinct record
    emsd_schema = {
        "name": "EMSD Consultancy Records Extractor",
        "baseSelector": "div.table_wrapper", 
        "fields": [
            {"name": "agreement_no", "selector": "tr:nth-child(1) td", "type": "text"},
            {"name": "consultancy_title", "selector": "tr:nth-child(2) td a", "type": "text"},
            {"name": "document_url", "selector": "tr:nth-child(2) td a", "type": "attribute", "attribute": "href"},
            {"name": "consultancy_name", "selector": "tr:nth-child(3) td", "type": "text"},
            {"name": "consultancy_cost", "selector": "tr:nth-child(4) td", "type": "text"},
            {"name": "award_date", "selector": "tr:nth-child(5) td", "type": "text"},
            {"name": "estimated_completion_date", "selector": "tr:nth-child(6) td", "type": "text"}
        ]
    }

    # 3. Apply configurations to extract data
    run_config = CrawlerRunConfig(
        word_count_threshold=0, 
        #content_filter=None, 
        extraction_strategy=JsonCssExtractionStrategy(schema=emsd_schema),
        magic=True,
        wait_for="css:.table, table, .content_block",  # Wait for table or content container
        delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
        js_code="window.scrollTo(0, document.body.scrollHeight);"
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://www.emsd.gov.hk/en/tenders_contracts_and_consultancies/tender_notices/award_of_consultancies/index.html",
            config=run_config
        )
        
        if result.success:
            data = json.loads(result.extracted_content)
            #data['department']='emsd'

            if isinstance(data, list):
                for record in data:
                    record['department'] = 'emsd'
                    record['type'] = 'consultancy'

                    with open('gov_emsd.json', "a") as f:
                
                # 2. Dump individual record dictionary as a single JSON line
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')

            
        else:
            print(f"Extraction failed: {result.error_message}")

        

if __name__ == "__main__":
    asyncio.run(main())
