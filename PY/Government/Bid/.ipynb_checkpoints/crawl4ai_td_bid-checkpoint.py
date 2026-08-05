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
    schema = {
        "name": "Tender Bid Invitation",
        "baseSelector": "tr",    # Repeated elements
        "fields": [
            {
                "name": "Reference",
                "selector": "td:nth-child(2)",
                "type": "text"
            },
            {
                "name": "Subject",
                "selector": "td:nth-child(3)",
                "type": "text"
            },
            {
                "name": "Subject_link",
                "selector": "a",
                "type": "attribute",
                "attribute": "href"
            },
            #             {
            #     "name": "Issue Date",
            #     "selector": "td:nth-child(1)",
            #     "type": "text"
            # },
            #       {
            #     "name": "Description",
            #     "selector": "td:nth-child(3)",
            #     "type": "text"
            # },
          {
                "name": "Closing Date",
                "selector": "td:nth-child(1)",
                "type": "text"
            }
        ]
    }

    			

    # 2. Create the extraction strategy
    extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)
    
    # 2. Attach the strategy to your run config
    config = CrawlerRunConfig(
        #extraction_strategy=extraction_strategy,
         magic=True,            # Simulates human interactions and bypasses overlays
        #user_agent_mode="random"  # Dynamically rotates realistic user agents
        simulate_user=True,       # Generates organic page activity
        override_navigator=True,   # Masks the automation signatures
        table_score_threshold=2,
        extraction_strategy=extraction_strategy
    )
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.td.gov.hk/en/tender_notices/tender_notices/index.html", 
            config=config
        )
        
        if result.success:
            # The structured data is stored in 'extracted_content'
            data = json.loads(result.extracted_content)
            #print(json.dumps(data, indent=2))
            #print(result.tables)
            #print(result.links)
            #for link in result.links['internal']:
                #print(f"URL: {link['href']} | Text: {link['text']}")

            #print(result.extracted_content)
            #print(pd.DataFrame(data).iloc[1:,:])
            pd.DataFrame(data).to_csv('TD_BID_20260617.csv')
            #print(data)

if __name__ == "__main__":
    asyncio.run(main())