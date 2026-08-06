import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy, VirtualScrollConfig
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

js_infinite_scroll_life = """
(async () => {
    let lastHeight = document.body.scrollHeight;
    let noChangeCount = 0;

    while (noChangeCount < 4) {
        // 1. Scroll to the bottom
        window.scrollTo(0, document.body.scrollHeight);

        // 2. Wait 1.5s for the #load_more spinner to process
        await new Promise(resolve => setTimeout(resolve, 1500));

        // 3. Check if new content was added
        let currentHeight = document.body.scrollHeight;
        if (currentHeight === lastHeight) {
            noChangeCount++;
        } else {
            noChangeCount = 0;
            lastHeight = currentHeight;
        }

        // 4. Monitor #load_more spinner state
        const spinner = document.querySelector('#load_more');
        if (spinner && window.getComputedStyle(spinner).display === 'none' && noChangeCount > 0) {
            console.log('[JS] #load_more is hidden and height is stable.');
        }
    }
})();
"""


# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str, file_name):
    async with AsyncWebCrawler() as crawler:
        
        # --- STAGE 1: Extract URLs from Level 1 ---
        print(f"[L1] Crawling index: {l1_start_url}")

        virtual_config = VirtualScrollConfig(
            container_selector="div.m-search-result-item--event",      # CSS selector for scrollable container
            scroll_count=1000,                 # Number of scrolls to perform
            scroll_by="container_height",    # How much to scroll each time
            wait_after_scroll=0.8           # Wait time (seconds) after each scroll
        )

        
        l1_config = CrawlerRunConfig(
            #table_extraction=table_strategy, 
            extraction_strategy=JsonCssExtractionStrategy(l1_css_schema),
            virtual_scroll_config=virtual_config,
            cache_mode=True
            #magic=True,
            #wait_for="div.rl-light-container",  # Wait for table or content container
            #delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
            #js_code="window.scrollTo(0, document.body.scrollHeight);",
            #js_code=js_infinite_scroll_life #,
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



