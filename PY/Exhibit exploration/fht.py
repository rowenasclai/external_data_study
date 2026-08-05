import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
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
    "baseSelector": "div.ex-result > div.ex-body",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "exhibitor",
            "selector": "div.company",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "booth",
            "selector": "div.stand p",           # Selector for the actual L2 URL
            "type": "text"
        },
     {
            "name": "country",
            "selector": "div.country p",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "category",
            "selector": "div.category p",           # Selector for the actual L2 URL
            "type": "text"
        }
    ]
}




# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str, file_name):
    async with AsyncWebCrawler() as crawler:
        
        # --- STAGE 1: Extract URLs from Level 1 ---
        print(f"[L1] Crawling index: {l1_start_url}")
        l1_config = CrawlerRunConfig(
            #table_extraction=table_strategy, 
            extraction_strategy=JsonCssExtractionStrategy(l1_css_schema),
            cache_mode=True,
            magic=True,
            wait_for="div.ex-result",  # Wait for table or content container
            delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
            js_code="window.scrollTo(0, document.body.scrollHeight);"
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

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.fhtevent.com/food/2026/en/list_participants.asp?pz=249",'exhibit_fht.json'))



