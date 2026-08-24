import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy, VirtualScrollConfig,CacheMode
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
    "baseSelector": "div.all_list > ul.zs_list > li",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "exhibitor",
            "selector": "div.right h3",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "exhibition_area",
            "selector": "dl.dl1 dd",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "exhibition_url",
            "selector": "a",           # Selector for the actual L2 URL
            "type": "attribute",
            "attribute":"href"
        },
     {
            "name": "hall",
            "selector": "dl.guan dd",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "booth",
            "selector": "dl.hao dd",           # Selector for the actual L2 URL
            "type": "text"
        }
        ,
        {
            "name": "description",
            "selector": "dl.dl1 dd",           # Selector for the actual L2 URL
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
            container_selector="div.tree-row-right",      # CSS selector for scrollable container
            scroll_count=1000,                 # Number of scrolls to perform
            scroll_by="container_height",    # How much to scroll each time
            wait_after_scroll=0.8           # Wait time (seconds) after each scroll
        )

        
        l1_config = CrawlerRunConfig(
            #table_extraction=table_strategy, 
            magic=True,
            extraction_strategy=JsonCssExtractionStrategy(l1_css_schema),
            wait_for="css:ul.zs_list li div.right h3",
            delay_before_return_html=2.5,
            wait_until="domcontentloaded",
            page_timeout=30000,
            cache_mode=CacheMode.BYPASS
            #wait_until="networkidle"
            #virtual_scroll_config=virtual_config,
            #cache_mode=True,
            #wait_for="css:ul.zs_list li"
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


        with open(file_name, "a") as f:
            json.dump(l1_data, f,indent=1, default=str,ensure_ascii=False)             
            f.write('\n')  
        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(final_dataset, indent=2))

for i in range(1,250):
# Run the pipeline with your initial L1 table input URL
    asyncio.run(run_decoupled_crawl("https://exhibitors.cioe.cn/gwen/index.html?zq=&zg=&zsqy=&zslx=&cxtj=&zpfw=&pageindex="+str(i)+"&pagesize=20#dingwei",'cioe_cn_v1.json'))


