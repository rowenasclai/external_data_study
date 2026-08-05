import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re
from langchain_ollama import OllamaLLM
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

# =====================================================================
# 1. DEFINE SCHEMAS
# =====================================================================

# L1 Schema: Only targets the links we need to jump into

L1_schema = {
    "name": "Tender Notices Extractor",
    # Target each individual repeating data row container
    "baseSelector": "div.resultDataContainerBox div.data",
    "fields": [
        {
            "name": "type",
            "selector": "div.typeData",
            "type": "text"
        },
        {
            "name": "contract_ref",
            "selector": "div.contractData",
            "type": "text"
        },
        {
            "name": "title",
            "selector": "div.titleData a", # Grabs text inside the anchor link
            "type": "text"
        },
        {
            "name": "link",
            "selector": "div.titleData a", # Grabs the actual URL path
            "type": "attribute",
            "attribute": "href"
        },
        {
            "name": "publish_date",
            "selector": "div.closingDateData",
            "type": "text"
        }
    ]
}

L2_schema = {
    "name": "Tender Notices Details Extractor",
    # Target each individual repeating data row container
    "baseSelector": "div.contentContainer",
    "fields": [
        {
            "name": "title",
            "selector": "div.componentTitle",
            "type": "text"
        },
        {
            "name": "paragraph 1",
            "selector": "p",
            "type": "text"
        },
        {
            "name": "paragraph 2",
            "selector": "p::nth-child(2)", # Grabs text inside the anchor link
            "type": "text"
        }
    ]
}

#strategy = JsonCssExtractionStrategy(schema=schema)


# =====================================================================
# 2. RUN PIPELINE
# =====================================================================

async def run_decoupled_crawl(l1_start_url: str):
    async with AsyncWebCrawler() as crawler:
        
        # --- STAGE 1: Extract URLs from Level 1 ---
        print(f"[L1] Crawling index: {l1_start_url}")
        l1_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(L1_schema),
            cache_mode=True,
            magic=True,
        wait_for="div.resultDataContainerBox",  # Wait for table or content container
        delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
        js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        l1_result = await crawler.arun(url=l1_start_url, config=l1_config)
        
        if not l1_result.success or not l1_result.extracted_content:
            print("Failed to parse L1 or no URLs found.")
            return

        # Parse the JSON string out of the L1 result
        l1_data = json.loads(l1_result.extracted_content)

        l2_urls = ['https://www.hongkongairport.com'+item['link'] for item in l1_data if item.get('link')]
        l2_ref = [item['contract_ref'] for item in l1_data if item.get('contract_ref')]
        l2_dt = [item['publish_date'] for item in l1_data if item.get('publish_date')]
        l2_title = [item['title'] for item in l1_data if item.get('title')]
        l2_type = [item['type'] for item in l1_data if item.get('type')]
        
        
        print(f"[L1] Discovered {len(l2_urls)} deep links to process.")
        if not l2_urls:
            return

        print("[L2] Beginning batch crawl on extracted target links...")
        l2_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(L2_schema),
            cache_mode=True,
            delay_before_return_html=3.0,  
            wait_for="div.iw_section",
            js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        
        # arun_many executes the array concurrently across your browser instances
        l2_results = await crawler.arun_many(urls=l2_urls, config=l2_config)
        
        llm = ChatOllama(
        base_url="http://localhost:11434/",
        model="llama3.1:8b",     # Fast 8B parameter model
        temperature=0,          # 0 prevents hallucinations in data extraction
        format="json"           # CRITICAL: Hard enforces valid JSON output
    )

         
        # Combine the results
        final_dataset = []
        for url, res, ref, dt, title, type1, l_data in zip(l2_urls, l2_results, l2_ref,l2_dt,l2_title,l2_type, l1_data):
            if res.success : 
                raw_lines_list = [line.strip() for line in res.markdown.split('\n') if line.strip()]
                # prompt = "Based on the example provided and other common company name format, try to identify company who got the contract award from the input paragraph. For example, we should extract 'China Harbour Engineering Company Limited' from this paragraph: 'Notice is hereby given that the Airport Authority of HKIA Tower, 1 Sky Plaza Road, Hong Kong International Airport, Lantau, Hong Kong awarded Contract E3002 for Bus Terminus at SkyPier Terminal to China Harbour Engineering Company Limited of 19/F, China Harbour Building, 370-374 King’s Road, North Point, Hong Kong on 13 July 2026.  The awarded contract sum was HK$75,924,123.' \n Valid examples of company name include: Roctec Technology Limited, AECOM Asia Company Limited, ATAL Engineering Limited. No need to show any explanation. :"

                system_instruction = (
        "You are a data transformation engine. Analyze the input data and organize it into a new JSON format. "
        "Your output must be a valid JSON object and nothing else. Do not include markdown code blocks like ```json. "
        "The output JSON structure MUST match this exact schema format:\n"
        "{\n"
        "  \"ref\": \"string\",\n"
        "  \"award_contractor\": \"string\",\n"
        "  \"contractor address\": \"string\",\n"
        "  \"estimated contract value\": <currency>,\n"
        "  \"project_summaries\": [\n"
        "     { \"ref\": \"string\", \"short_title\": \"string\" }\n"
        "  ]\n"
        "}"
    )

                human_query = f"Transform this paragraph: {json.dumps(res.extracted_content)}"

                messages = [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=human_query)
                ]

                print("Requesting fast-structured JSON from Llama 3.1 8B...\n")
                print("=== Raw Streaming JSON Output ===")
    
    # 4. Stream chunks in real-time
                full_response = ""
                for chunk in llm.stream(messages):
                    content = chunk.content
                    full_response += content
                    #print(content, end="", flush=True)
    
                print("\n\n=== Verification ===")
                try:
        # Validate that the final string output parses correctly back into Python
                    parsed_json = json.loads(full_response)
                    parsed_json["department"] = "hkaa"
                    parsed_json["award_date"] = dt
                    parsed_json["url"] = url
                    parsed_json["type"] = type1
                    parsed_json["subject"] = title

                    with open('gov_hkaa.json', "a") as f:
                # 2. Dump individual record dictionary as a single JSON line
                        json.dump(parsed_json, f,indent=1, default=str,ensure_ascii=False)
                        f.write('\n')

                    
                    #print("Success! The output is 100% valid JSON.")
                    #print(f"json.dumps({parsed_json}, indent=2)")
                    #print(f"Total counted: {parsed_json.get('total_contracts_found')}")
                except json.JSONDecodeError:
                    print("Error: The output was structurally malformed.")

                

                # with open('gov_hkaa.json', "a") as f:
                # # 2. Dump individual record dictionary as a single JSON line
                #     json.dump(record, f,indent=1, default=str)
                #     f.write('\n')

                # print(record)

        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(l1_data, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://www.hongkongairport.com/en/airport-authority/tender-notices/notice-of-contract-award.page"))


