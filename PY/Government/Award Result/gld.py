import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import re
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from crawl4ai import DefaultTableExtraction

import os

os.chdir('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/gov_cntract/Raw/data')

# =====================================================================
# TSD
# 1. DEFINE SCHEMAS
# =====================================================================

# L1 Schema: Only targets the links we need to jump into

l1_css_schema = {
    "name": "L1_Link_Extractor",
    "baseSelector": "div.layout-page-container tbody tr",  # Selector for your L1 grid/table rows
    "fields": [
        {
            "name": "department",
            "selector": "span.deptName",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "ref",
            "selector": "td:nth-child(1)",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "span_count",
            "selector": "td",
            "type": "attribute",
            "attribute": "rowspan"
        },
     {
            "name": "tendering_procedure",
            "selector": "td:nth-child(2)",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "particulars",
            "selector": "td:nth-child(3)",           # Selector for the actual L2 URL
            "type": "text"
        },
        {
            "name": "Contractor(s) & Address(es)",
            "selector": "td:nth-child(4), td.hangingIndent:nth-child(1)",           # Selector for the actual L2 URL
            "type": "text"
        }
        ,
        {
            "name": "quantity",
            "selector": "td:nth-child(5)",           # Selector for the actual L2 URL
            "type": "text"
        }
        ,
        {
            "name": "Amount / Contract Award Date",
            "selector": "td:nth-child(6)",           # Selector for the actual L2 URL
            "type": "text"
        }
    ]
}

table_strategy = DefaultTableExtraction(
        table_score_threshold=7,  # Higher scores target actual data grids instead of layout boxes
        min_rows=1,
        min_cols=2
    )


js_flatten_rowspan = """
(() => {
    const table = document.querySelector('table');
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tr'));
    let matrix = [];

    rows.forEach((row, rowIndex) => {
        if (!matrix[rowIndex]) matrix[rowIndex] = [];
        let currentCellIndex = 0;

        Array.from(row.cells).forEach(cell => {
            // Find the first empty spot in the row matrix
            while (matrix[rowIndex][currentCellIndex] !== undefined) {
                currentCellIndex++;
            }

            const rowspan = parseInt(cell.getAttribute('rowspan'), 10) || 1;
            const colspan = parseInt(cell.getAttribute('colspan'), 10) || 1;

            // Clone and map cells across rows/columns where rowspan hits
            for (let r = 0; r < rowspan; r++) {
                const targetRowIndex = rowIndex + r;
                if (!matrix[targetRowIndex]) matrix[targetRowIndex] = [];

                for (let c = 0; c < colspan; c++) {
                    matrix[targetRowIndex][currentCellIndex + c] = cell;
                }
            }
            currentCellIndex += colspan;
        });
    });

    // Reconstruct the actual HTML tables using the flattened matrix
    rows.forEach((row, rowIndex) => {
        row.innerHTML = ''; // Wipe out uneven cells
        matrix[rowIndex].forEach(cell => {
            if (cell) {
                // Remove the rowspan marker so it behaves as a normal single cell
                const newCell = cell.cloneNode(true);
                newCell.removeAttribute('rowspan');
                row.appendChild(newCell);
            }
        });
    });
    return true;
})();
"""



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
            wait_for="div.layout-page-container",  # Wait for table or content container
            delay_before_return_html=3.0,                  # Allow 3s for dynamic JS to settle
            #js_code="window.scrollTo(0, document.body.scrollHeight);"
            js_code=js_flatten_rowspan
        )
        l1_result = await crawler.arun(url=l1_start_url, config=l1_config)

        #l1_result = await crawler.arun(url=l1_start_url, config=l1_config)

        # for t_idx, table in enumerate(l1_result.tables):
        #     print(json.dumps(table, indent=2))
        
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

        l1_contract_address = [item['Contractor(s) & Address(es)'] for item in l1_data if item.get('Contractor(s) & Address(es)')]

        preserve_ref=''
        preserve_tendering_procedure=''
        preserve_particulars=''
        dept=''
    
    # 4. Stream chunks in real-time          

        if isinstance(l1_data, list):
            for record in l1_data:
                #print(record)
                if record.get("department"):
                    #record['department']=record.get("department")
                    dept=record.get("department")

                elif not record.get("department"):
                    record['department'] =dept
                #print(record)
                
                if record.get("Contractor(s) & Address(es)"):
                    record=record
                elif record.get("span_count") and int(record.get('span_count')) > 1:
                    preserve_ref=record["ref"]
                    preserve_procedure=record["tendering_procedure"]
                    preserve_particulars=record["particulars"]
                elif not record.get("span_count") and record.get("tendering_procedure"):
                    record['span_count'] = 0
                    tmp=record['Contractor(s) & Address(es)']
                    record['Contractor(s) & Address(es)']=record["ref"]
                    record['quantity']=record["tendering_procedure"]
                    record['Amount / Contract Award Date']=record["particulars"]
                    record['ref']=preserve_ref
                    record['tendering_procedure']=preserve_tendering_procedure
                    record['description']=preserve_particulars

                record['type'] = 'contract_award'


                #print(record)

                system_instruction = (
        "You are a data transformation engine. Analyze the input data and organize it into a new JSON format. "
        "Your output must be a valid JSON object and nothing else. Do not include markdown code blocks like ```json. "
        "The output JSON structure MUST match this exact schema format:\n"
        "{\n"
        "  \"award_contractor\": \"string\",\n"
        "  \"contractor address\": \"string\",\n"
        "  \"contract_amount\": \"string\",\n"
        "  \"contract_award_date\": \"string\"\n"
        "  ]\n"
        "}"
    )
                #print(str(record.get('Amount / Contract Award Date')))
                human_query = f"Transform this paragraph: {str(record.get('Contractor(s) & Address(es)'))}{str(record.get('Amount / Contract Award Date'))}"

                messages = [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=human_query)
                ]

                print("Requesting fast-structured JSON from Llama 3.1 8B...\n")
                print("=== Raw Streaming JSON Output ===")

                full_response = ""
                
                for chunk in llm.stream(messages):
                    content = chunk.content
                    full_response += content

                    try: 
                         # Validate that the final string output parses correctly back into Python
                        parsed_json = json.loads(full_response)
                        #print(parsed_json)
                        record["awardee"] = parsed_json['award_contractor']
                        record["contractor_address"] = parsed_json['contractor address']
                        record["sum"] = parsed_json['contract_amount']
                        record["award_date"] = parsed_json['contract_award_date']

                    except:
                        pass
     
                # try:
                #     record['award_date']=record['td:nth-child(6)'][record['td:nth-child(6)'].index('<br/><br/>'):]
                #     record['contract_sum']=record['td:nth-child(6)'][:record['td:nth-child(6)'].index('<br/>')]

                # except:
                #     pass
               
                #print(record)

                with open(file_name, "a") as f:
                    #f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    json.dump(record, f,indent=1, default=str,ensure_ascii=False)
                    f.write('\n')     
        
        print("\n=== FINAL EXTRACTED DATA ===")
        #print(json.dumps(final_dataset, indent=2))

# Run the pipeline with your initial L1 table input URL
asyncio.run(run_decoupled_crawl("https://pcms2.gld.gov.hk/iprod/#/scn00101",'gov_gld.json'))



