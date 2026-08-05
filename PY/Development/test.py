import asyncio
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMExtractionStrategy, LLMConfig

# 1. Define your strict data schema structure
class ProjectDetails(BaseModel):
    department: str = Field(default="dsd", description="Government department code")
    type: str = Field(default="contract_awarded", description="Document type")
    contract_title: str = Field(None, description="Full contract or project title")
    date_of_award: str = Field(None, description="Date when contract was awarded")
    contractor: str = Field(None, description="Awarded contractor or joint venture name")
    date_of_commencement: str = Field(None, description="Contract commencement date")
    anticipated_completion_date: str = Field(None, description="Anticipated completion date")
    contract_sum: str = Field(None, description="Contract sum or monetary amount in HKD")
    project_office: str = Field(None, description="Responsible project division or office")
    source_url: str = Field(None, description="Source web page URL")

async def extract_with_local_ollama(target_url: str):
    # 2. Point LLMConfig directly to your local Ollama port instance
    ai_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            # Prefix with 'ollama/' followed by your exact downloaded model tag
            provider="ollama/mistral", 
            # Define your local server link (Default Ollama endpoint)
            base_url="http://localhost:11434", 
            api_token=None # No API key needed for local runs
        ),
        schema=ProjectDetails.model_json_schema(),
        instruction="""
        Extract all contract award details from the DSD webpage into a JSON list matching the Pydantic schema.
        Fields to extract: contract_title, date_of_award, contractor, date_of_commencement, 
        anticipated_completion_date, contract_sum, project_office.
        """,
        extraction_type="schema",
        extra_args={
            # Local Ollama endpoint
            "temperature": 0.0
        }
    )
    
    # 3. Attach strategy to runtime configs
    config = CrawlerRunConfig(
        extraction_strategy=ai_strategy,
        cache_mode=True,
        #magic=True,
        wait_for="body",  # Wait for table or content container
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
asyncio.run(extract_with_local_ollama("https://www.dsd.gov.hk/EN/Our_Projects/Contracts_Consultancies_Awarded/contractsproject443.html"))
