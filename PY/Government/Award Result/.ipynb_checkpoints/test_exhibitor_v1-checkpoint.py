import asyncio
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMExtractionStrategy, LLMConfig
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

L1_schema = {
    "name": "Tender Notices Extractor",
    # Target each individual repeating data row container
    "baseSelector": "div.l-content div.lshowcase-thumb",
    "fields": [
        {
            "name": "exhibitor_details",
            "selector": "",
            "type": "text"
        }
    ]
}

# 1. Define your strict data schema structure
async def run_decoupled_crawl(l1_start_url: str):
    async with AsyncWebCrawler() as crawler:
        
        # --- STAGE 1: Extract URLs from Level 1 ---
        print(f"[L1] Crawling index: {l1_start_url}")
        l1_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(L1_schema),
            cache_mode=True,
            magic=True,
        wait_for="div.l-content",  # Wait for table or content container
        delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
        js_code="window.scrollTo(0, document.body.scrollHeight);"
        )
        l1_result = await crawler.arun(url=l1_start_url, config=l1_config)
        
        if not l1_result.success or not l1_result.extracted_content:
            print("Failed to parse L1 or no URLs found.")
            return

        # Parse the JSON string out of the L1 result
        l1_data = json.loads(l1_result.extracted_content)

        llm = ChatOllama(
        base_url="http://localhost:11434/",
        model="llama3.1:8b",     # Fast 8B parameter model
        temperature=0,          # 0 prevents hallucinations in data extraction
        format="json"           # CRITICAL: Hard enforces valid JSON output
    )

         
        # Combine the results
        final_dataset = []
        for res in zip(l1_data):
            if res.success : 
                #raw_lines_list = [line.strip() for line in res.markdown.split('\n') if line.strip()]

                system_instruction = (
        "You are a data transformation engine. Analyze the input data and organize it into a new JSON format. "
        "Your output must be a valid JSON object and nothing else. Do not include markdown code blocks like ```json. "
        "The output JSON structure MUST match this exact schema format:\n"
        "{\n"
        "  \"exhibitor\": \"string\",\n"
        "  \"exhibitor_description\": \"string\"}\n"
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
                    print(content, end="", flush=True)
    
                print("\n\n=== Verification ===")
               
                # print(record)

        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(l1_data, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://techsposingapore.sg/exhibitors"))


# Execute the local pipeline script
asyncio.run(extract_with_local_ollama("https://techsposingapore.sg/exhibitors"))
