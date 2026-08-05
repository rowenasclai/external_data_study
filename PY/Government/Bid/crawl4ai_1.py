import asyncio

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
import pandas as pd

async def main():
    # Configure the browser with stealth techniques
    browser_config = BrowserConfig(
        enable_stealth=True,
        headless=False,
        # Playwright-stealth injects scripts to mask automated behavior
        use_managed_browser=True 
    )

    click_by_text_js = """
    const targetText = "TENDER NOTICES"; 
    const links = Array.from(document.querySelectorAll('a'));
    const targetLink = links.find(el => el.textContent.trim().includes(targetText));
    if (targetLink) targetLink.click();
    """

    #adapter = UndetectedAdapter()
    #strategy = AsyncPlaywrightCrawlerStrategy(browser_config, browser_adapter=adapter)
    
    # Run the crawler with Magic Mode enabled
    run_config = CrawlerRunConfig(
        magic=True,            # Simulates human interactions and bypasses overlays
        #user_agent_mode="random"  # Dynamically rotates realistic user agents
        simulate_user=True,       # Generates organic page activity
    override_navigator=True,   # Masks the automation signatures
        table_score_threshold=2,
        js_code=click_by_text_js
    )

    #async def click_link():
    # run_config = CrawlerRunConfig(
    #     js_code=click_by_text_js#,
    #     #wait_for="css:.new-data"  # Wait for content to load
    # )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://www.ha.org.hk/visitor/ha_visitor_index.asp?Content_ID=2001&Lang=ENG&Dimension=100&Ver=HTML", config=run_config)

        #print(result.markdown)
        print(result.content)
        #print(result.extracted_content)

        #print(result.links.get("internal", []))

        #print(result.links.get("internal", []))

        # all_links = result.links.get("internal", []) + result.links.get("external", []) #
            
        #     # The exact anchor text you are looking for
        # target_text = "TENDER NOTICES"
            
        #     # Match exact text (case-insensitive approach shown)
        # matched_links = [
        #     link["href"] for link in all_links 
        #     if link.get("text", "").strip().upper() == target_text.upper()
        # ]
            
        #print("Matched URLs:", matched_links)
        
        #print(result.markdown)

    # async with AsyncWebCrawler(config=browser_config) as crawler:
    #     result = await crawler.arun(url="https://www.ha.org.hk/haho/ho/bssd/TN_257201_000347580a.htm", config=run_config)
    #     #print(result.markdown)
    #     #print(result)
    #     #print(result.tables)
    #     #print(result.tables[0]['headers'])
    #     #print(result.tables[0]['rows'])
    #     df = pd.DataFrame(result.tables[0]['rows'])

    #     df.to_csv('tmp.csv')

        
        #print(result.tables)
        #y=result.tables
        #print(type(y))

if __name__ == "__main__":
    asyncio.run(main())
