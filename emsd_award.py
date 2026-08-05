from pydantic import BaseModel, Field
from typing import List
import pandas as pd

# Define the schema for a single item
class ProductSchema(BaseModel):
    ref: str = Field(..., description="The Reference Number for Contract")
    subject: str = Field(..., description="The subject of the invitation bid")
    closing_dt: str = Field(..., description="Bid Closing Date")

# Define a container schema if the page contains a list of items
class PageSchema(BaseModel):
    products: List[ProductSchema]


import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def main():
    # 1. Map your schema fields to CSS selectors on the webpage
    extraction_strategy = JsonCssExtractionStrategy(
        schema=PageSchema.model_json_schema()#, # Convert Pydantic to JSON schema
        #base_selector="tr"        # The wrapper element for each product
        #css_selector=".athing:nth-child(-n+30)"
    )
    
    browser_config = BrowserConfig(
        headless=False,
        text_mode=False,           # CRITICAL: Keep raw HTML text tags alive
        light_mode=False,          # Prevents stripping structural css styling
    )

    schema = {
        "name": "Tender Award",
        "baseSelector": "div.table_wrapper",    # Repeated elements
        "fields": [
            {
                "name": "Agreement No.",
                "selector": "tr td",
                "type": "text"
            },
            {
                "name": "Consultancy Title",
                "selector": "tr:nth-child(2) td",
                "type": "text"
            },
            {
                "name": "Consultancy Name",
                "selector": "tr:nth-child(3) td",
                "type": "text"
            },
            {
                "name": "Consultancy_Cost",
                "selector": "tr:nth-child(4) td",
                "type": "text"
            },
             {
                "name": "Award Date",
                "selector": "tr:nth-child(5) td",
                "type": "text"
            },
             {
                "name": "Estimated Completion Date",
                "selector": "tr:nth-child(6) td",
                "type": "text"
            }
            
           # {
            #    "name": "Subject_link",
             #   "selector": "a",
              #  "type": "attribute",
               # "attribute": "href"
            #},
            #             {
            #     "name": "Issue Date",
            #     "selector": "td:nth-child(3)",
            #     "type": "text"
            # },
 #         {
  #              "name": "Award Date",
   #             "selector": "td:nth-child(3)",
    #            "type": "text"
     #       }
        ]
    }

    		

    # 2. Create the extraction strategy
    extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)
    
    # 2. Attach the strategy to your run config
    config = CrawlerRunConfig(
        #extraction_strategy=extraction_strategy,
        css_selector="div.table_wrapper",
        magic=True,            # Simulates human interactions and bypasses overlays
        #user_agent_mode="random"  # Dynamically rotates realistic user agents
        simulate_user=True,       # Generates organic page activity
        override_navigator=True,   # Masks the automation signatures
        table_score_threshold=2,
        extraction_strategy=extraction_strategy,
        word_count_threshold=0,             
        process_iframes=True
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
    url="https://www.emsd.gov.hk/en/tenders_contracts_and_consultancies/tender_notices/award_of_consultancies/index.html", 
            config=config
        )
        print(result)
        print(result.extracted_content)
        
        if result.success:
            # The structured data is stored in 'extracted_content'
            data = json.loads(result.extracted_content)
            print(result.extracted_content)

            #pd.DataFrame(data).to_csv('EMSD_AWARD_20260617.csv')
            #print(data)

if __name__ == "__main__":
    asyncio.run(main())