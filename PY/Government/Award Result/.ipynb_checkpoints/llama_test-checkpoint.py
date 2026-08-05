import json
import asyncio
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

async def main():
    # 1. Your Crawl4AI data batch
    scraped_data = [
        {
            "content": "Notice is hereby given that Airport Authority of HKIA Tower, 1 Sky Plaza Road, Hong Kong International Airport, Lantau, Hong Kong has awarded a contract for Term Contract T26M222 Maintenance, Improvement and Refurbishment Works for Car Park and Vehicle Access Control System (Tender Ref: PRO/T189/26/MP) to PCCW Technical Services Limited at 23/F Lincoln House, Taikoo Place, 979 King’s Road, Quarry Bay, Hong Kong on 15 July 2026. This Term Contract is for a contract period from 17 July 2026 to 16 July 2030. The estimated contract value excluding price fluctuation for this Term Contract is HK$30.07 million."
        }
    ]

    # 2. Configure ChatOllama for forced JSON output (Runs lightning fast on 8B)
    llm = ChatOllama(
        base_url="http://localhost:11434/",
        model="llama3.1:8b",     # Fast 8B parameter model
        temperature=0,          # 0 prevents hallucinations in data extraction
        format="json"           # CRITICAL: Hard enforces valid JSON output
    )

    # 3. System prompt providing the strict schema to follow
    system_instruction = (
        "You are a data transformation engine. Analyze the input data and organize it into a new JSON format. "
        "Your output must be a valid JSON object and nothing else. Do not include markdown code blocks like ```json. "
        "The output JSON structure MUST match this exact schema format:\n"
        "{\n"
        "  \"total_contracts_found\": <integer>,\n"
        "  \"ref\": \"string\",\n"
        "  \"award_contractor\": \"string\",\n"
        "  \"contractor address\": \"string\",\n"
        "  \"estimated contract value\": <currency>,\n"
        "  \"project_summaries\": [\n"
        "     { \"ref\": \"string\", \"short_title\": \"string\" }\n"
        "  ]\n"
        "}"
    )

    human_query = f"Transform this data payload: {json.dumps(scraped_data)}"

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
    try:
        # Validate that the final string output parses correctly back into Python
        parsed_json = json.loads(full_response)
        print("Success! The output is 100% valid JSON.")
        print(f"Total counted: {parsed_json.get('total_contracts_found')}")
    except json.JSONDecodeError:
        print("Error: The output was structurally malformed.")

if __name__ == "__main__":
    # First make sure you ran: ollama pull llama3.1
    asyncio.run(main())
