import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy, VirtualScrollConfig, CacheMode
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from crawl4ai import DefaultTableExtraction

# =====================================================================
# TSD
# 1. DEFINE SCHEMAS
# =====================================================================

# L1 Schema: Only targets the links we need to jump into

l1_css_schema = {
    "name": "L1_Link_Extractor",
    "baseSelector": "div.ex-event-search-result-item__content",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "event_date and location",
            "selector": "div.ex-event-search-result-item__date-location-container text-muted",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "event",
            "selector": "div.ex-event-search-result-item__text-container",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "event_url",
            "selector": "div.ex-event-search-result-item__text-container a",           # Selector for the actual L2 URL
            "type": "attribute",
            "attribute":"href"
        },
     {
            "name": "event_description",
            "selector": "div.ex-event-search-result-item__location-container text-muted",           # Selector for the actual L2 URL
            "type": "text"
        }
    ]
}

SENTRY_SCROLL_JS = """
async () => {
    const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    
    let lastEventCount = 0;
    let noChangeCount = 0;
    const maxNoChange = 5;

    for (let i = 0; i < 30; i++) { // Up to 30 page batches (25 events each)
        // Locate the IntersectionObserver sentry element
        const sentry = document.querySelector('.ex-event-search-results__sentry');
        
        if (sentry) {
            // Bring sentry into view to trigger React's IntersectionObserver
            sentry.scrollIntoView({ behavior: 'smooth', block: 'end' });
            await delay(1500); // Buffer for AJAX load to complete
        } else {
            window.scrollBy({ top: 1200, behavior: 'smooth' });
            await delay(800);
        }

        // Count current rendered result items
        const currentEventCount = document.querySelectorAll('.ex-event-search-result-item').length;
        
        if (currentEventCount === lastEventCount) {
            noChangeCount++;
            if (noChangeCount >= maxNoChange) {
                break; // Reached end of dynamic list
            }
        } else {
            noChangeCount = 0;
            lastEventCount = currentEventCount;
        }
    }
};
"""


# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str, file_name):
    async with AsyncWebCrawler() as crawler:
        
        # --- STAGE 1: Extract URLs from Level 1 ---
        print(f"[L1] Crawling index: {l1_start_url}")

        virtual_config = VirtualScrollConfig(
            container_selector="div.ex-event-search__container",      # CSS selector for scrollable container
            scroll_count=1000,                 # Number of scrolls to perform
            scroll_by="container_height",    # How much to scroll each time
            wait_after_scroll=0.8           # Wait time (seconds) after each scroll
        )

        
        l1_config = CrawlerRunConfig(
            #table_extraction=table_strategy, 
            extraction_strategy=JsonCssExtractionStrategy(l1_css_schema),
            #virtual_scroll_config=virtual_config,
            #cache_mode=True,
            cache_mode=CacheMode.BYPASS,
            #scan_full_page=True,        # Natively triggers window scrolling down
            #scroll_delay=3.8,
            #magic=True,
            wait_for="#mf-ev-root",  # Wait for table or content container
            delay_before_return_html=3.0,
            js_code=SENTRY_SCROLL_JS
            #delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
            #js_code="window.scrollTo(0, document.body.scrollHeight);",
            #js_code=WINDOW_SCROLL_JS #,
            #scan_full_page=True
            #js_code=AUTO_SCROLL_JS
            #js_code=js_flatten_rowspan
        )
        l1_result = await crawler.arun(url=l1_start_url, config=l1_config)
        
        if not l1_result.success or not l1_result.extracted_content:
            print("Failed to parse L1 or no URLs found.")
            return

        # Parse the JSON string out of the L1 result
        l1_data = json.loads(l1_result.extracted_content)

        # if isinstance(l1_data, list):
        #     for record in l1_data:
        #         # record['department'] = 'epd'
        #         # record['type'] = 'contract_awarded'
        #         # record['url'] = url

        #         try:
        #             record['exhibitor_name']=record['exhibitor'][:record['exhibitor'].index('<br/>')]

        #         except:
        #             pass

        #         try:
        #             record['exhibitor_loc']=record['industry'][:record['industry'].index('<br/>')]
        #             idx=record['industry'].index('<br/>')
        #             record['exhibitor_industry']=record['industry'][record['industry'].index('<br/>'):record['industry'].index('<br/>',idx+1)]
        #             idx2=record['industry'].index('<br/>',idx+1)
        #             record['exhibitor_url']=record['industry'][record['industry'].index('<br/>',idx2+1):]
                    

        #         except:
        #             pass
        #             #record['exhibitor']=record['exhibitor'][record['Contractor(s)'].index('<p>')+3:record['Contractor(s)'].index('</p>')] 

        #         with open(file_name, "a") as f:
        #             json.dump(record, f,indent=1, default=str,ensure_ascii=False)
        #             f.write('\n')    

        with open(file_name, "a") as f:
            json.dump(l1_data, f,indent=1, default=str,ensure_ascii=False)             
            f.write('\n')  
        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(final_dataset, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.messefrankfurt.com/frankfurt/en/event-search.html",'messe_frankfurt_event_list.json'))



