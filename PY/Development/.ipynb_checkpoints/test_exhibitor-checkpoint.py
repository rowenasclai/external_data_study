import asyncio
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMExtractionStrategy, LLMConfig

# 1. Define your strict data schema structure
class ProjectDetails(BaseModel):
    exhibitor: str = Field(default="N/A", description="Exhibitor name (Company)")
    description: str = Field(default="N/A", description="Exhibitor Description")
    source_url: str = Field(None, description="Source web page URL")

async def extract_with_local_ollama(target_url: str):
    # 2. Point LLMConfig directly to your local Ollama port instance
    ai_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            # Prefix with 'ollama/' followed by your exact downloaded model tag
            provider="ollama/llama3.1:8b", 
            # Define your local server link (Default Ollama endpoint)
            base_url="http://localhost:11434", 
            api_token=None # No API key needed for local runs
        ),
        schema=ProjectDetails.model_json_schema(),
        instruction="""
        Extract all exhibition details from the exhibition webpage into a JSON list matching the Pydantic schema. Session should be under "Thanks to our exhibitors! session."
        Fields to extract: exhibitors, exhibitor description.
        "The output JSON structure MUST match this exact schema format:\n"
        "{\n"
        "  \"exhibitor\": \"string\",\n"
        "  \"exhibitor_description\": \"string\"}\n"
        "  ]\n"
        """,
        extraction_type="json",
        extra_args={
            # Local Ollama endpoint
            "temperature": 0.0,
            "format":'json'
        }
    )
    
    # 3. Attach strategy to runtime configs
    config = CrawlerRunConfig(
        extraction_strategy=ai_strategy,
        cache_mode=True,
        #magic=True,
        wait_for="div.l-content",  # Wait for table or content container
        delay_before_return_html=3.0
    )
    
    async with AsyncWebCrawler() as crawler:
        print(f"Crawling and processing using local Ollama model...")
        result = await crawler.arun(url=target_url, config=config)
        
        if result.success and result.extracted_content:
            print("\n=== LOCAL AI EXTRACTED CONTENT ===")
            print(result.extracted_content)
        else:
            print(f"Extraction failed: {result.error_message}")

# Execute the local pipeline script
asyncio.run(extract_with_local_ollama("https://techsposingapore.sg/exhibitors"))
