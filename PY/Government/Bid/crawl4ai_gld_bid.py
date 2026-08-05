import os, sys
import asyncio, time
from crawl4ai import AsyncWebCrawler, CacheMode

from crawl4ai import RateLimiter

# Create a RateLimiter with custom settings
rate_limiter = RateLimiter(
    base_delay=(2.0, 10.0),  # Random delay between 2-4 seconds
    max_delay=60.0,         # Cap delay at 30 seconds
    max_retries=5,          # Retry up to 5 times on rate-limiting errors
    rate_limit_codes=[429, 503]  # Handle these HTTP status codes
)

# RateLimiter will handle delays and retries internally
# No additional setup is required for its operation


async def test_news_crawl():

    async with AsyncWebCrawler(
        headless=False,
        verbose=True,
        enable_stealth=True,
        user_agent_mode="random",
        user_agent_generator_config={
            "device_type": "mobile",
            "os_type": "android"
        },
        wait_until="networkidle"
    ) as crawler:
        url = "https://pcms2.gld.gov.hk/iprod/#/sta00305"       
        result = await crawler.arun(
            url,
            cache_mode=CacheMode.BYPASS,
            remove_overlay_elements=True,
            wait_for_images = True,
            screenshot=True,
        )
        if result.success:
            print(f"Content length: {len(result.markdown)}")
            # Save image in output directory
            with open(f"{__location__}/output/screenshot_{time.time()}.png", "wb") as f:
                f.write(base64.b64decode(result.screenshot))
                       
                        
if __name__ == "__main__":
    asyncio.run(test_news_crawl())