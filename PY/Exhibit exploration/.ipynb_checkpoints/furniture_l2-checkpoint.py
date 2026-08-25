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
    "baseSelector": "div.row.g-8",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "description",
            "selector": "article.ckediter",
            "type": "text"
        },
        {
            "name": "established_in",
            "selector": "table.table--noborder tr:nth-child(1) td",
            "type": "text"
        },
        {
            "name": "number_of_staff",
            "selector": "table.table--noborder tr:nth-child(2) td",
            "type": "text"
        },
        {
            "name": "support_oem",
            "selector": "table.table--noborder tr:nth-child(3) td",
            "type": "text"
        },
        {
            "name": "location",
            "selector": "table.table--noborder tr:nth-child(4) td",
            "type": "text"
        },
        {
            "name": "brands",
            "selector": "table.table--noborder tr:nth-child(5) td",
            "type": "text"
        },
        {
            "name": "website",
            "selector": "table.table--noborder tr:nth-child(6) td",
            "type": "text"
        }
    ]
}


JS_CLICK_NEXT = """
async () => {
    const nextBtn = document.querySelector('a.pager-right-next, a[aria-label*="Next Page"]');
    if (nextBtn && !nextBtn.classList.contains('disabled')) {
        nextBtn.click();
        // Wait for AJAX table content to start updating
        await new Promise(r => setTimeout(r, 2000));
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
            container_selector="div.tree-row-right",      # CSS selector for scrollable container
            scroll_count=1000,                 # Number of scrolls to perform
            scroll_by="container_height",    # How much to scroll each time
            wait_after_scroll=0.8           # Wait time (seconds) after each scroll
        )

        
        l1_config = CrawlerRunConfig(
            #table_extraction=table_strategy, 
            extraction_strategy=JsonCssExtractionStrategy(l1_css_schema),
            #virtual_scroll_config=virtual_config,
            cache_mode=True,
            magic=True,
            wait_until="domcontentloaded",
            wait_for="css:article.ckediter, css:table.table--noborder",
            #wait_for="css:table.list-table tbody tr td div.limit2",  # Wait for table or content container
            #wait_until="domcontentloaded",
            #wait_for="css:article.ckediter",
            delay_before_return_html=1.2#,                  # Allow 3s for dynamic JS to settle
            #js_code="window.scrollTo(0, document.body.scrollHeight);",
            #js_code=js_infinite_scroll_life #,
            #scan_full_page=True
            #js_code=AUTO_SCROLL_JS
            #js_code=JS_CLICK_NEXT
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
            json.dump(l1_data, f,#indent=1, default=str,
                      ensure_ascii=False)             
            f.write('\n')  
        
        delay = random.uniform(2.0, 6.0)
        await asyncio.sleep(delay)
        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(final_dataset, indent=2))

import pandas as pd

df1 = pd.read_csv("/Users/rowena/furniture_list.csv")
tmp=df1[df1['url'].isna()==False]

for i in range(448,len(tmp)-1):
    url=tmp['url'].iloc[i]
# Run the pipeline with your initial L1 table input URL
    asyncio.run(run_decoupled_crawl(url,'furniture_l2_v2.json'))


