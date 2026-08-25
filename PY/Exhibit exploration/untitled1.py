import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

# Direct URL extracted from the iframe
DIRECT_IFRAME_URL = "https://exhibitors.informamarkets-info.com/event/2026JGW/en-US/"

async def main():
    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1920,
        viewport_height=1080
    )

    run_config = CrawlerRunConfig(
        wait_until="domcontentloaded",
        # Set wait_for to the actual row/list container inside the Informa directory
        wait_for="css:table, css:.exhibitor-list, css:div.list",
        delay_before_return_html=2.0
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=DIRECT_IFRAME_URL, config=run_config)
        
        if result.success:
            print("Successfully accessed direct directory page!")
            # Inspect result.cleaned_html or run your extraction strategy here

file_name="jgw.json"

if __name__ == "__main__":
    asyncio.run(main())

    with open(file_name, "a") as f:
        json.dump(l1_data, f,indent=1, default=str,ensure_ascii=False)             
        f.write('\n')  
        
        


