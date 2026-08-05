import asyncio
import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

class Crawl4AICEDDExtractor:
    def __init__(self):
        self.base_url = "https://www.cedd.gov.hk/eng/tender-notices/contracts/contracts-awarded/index.html"
        
        # Configure Crawl4AI Browser
        self.browser_config = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Configure Crawl4AI Run Settings (Handles JS rendering)
        self.run_config = CrawlerRunConfig(
            wait_for="table, .content",
            delay_before_return_html=2.0
        )

    def parse_index_table(self, html_content: str):
        """Parse Stage 1 HTML table to extract summary fields & detail links."""
        soup = BeautifulSoup(html_content, "html.parser")
        records = []

        table = soup.find("table")
        if not table:
            return records

        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) < 3:
                continue

            ref_text = cols[0].get_text(strip=True)
            subject_text = cols[1].get_text(strip=True)
            award_date = cols[2].get_text(strip=True)

            if "Tender Reference" in ref_text or "Subject" in subject_text:
                continue

            # Extract 2nd URL (detail page link index-id-XXXX.html)
            detail_a = cols[1].find("a", href=True) or cols[0].find("a", href=True)
            detail_url = urljoin(self.base_url, detail_a["href"]) if detail_a else None

            records.append({
                "contract_no": ref_text,
                "subject": subject_text,
                "awarded_date": award_date,
                "detail_url": detail_url
            })

        return records

    def parse_detail_html(self, html_content: str):
        """Parse Stage 2 detail page HTML for contractor and sum fields."""
        soup = BeautifulSoup(html_content, "html.parser")
        page_text = soup.get_text(" ", strip=True)

        contractor_m = re.search(r"Contractor[:\s]*([^:\n]+?)(?=Contractor's Address|Quantity|Awarded Sum|$)", page_text, re.I)
        address_m = re.search(r"Contractor's Address[:\s]*([^:\n]+?)(?=Quantity|Awarded Sum|Description|$)", page_text, re.I)
        sum_m = re.search(r"Awarded Sum[^:\n]*[:\s]*([HK\$\d\.\sMmillion]+)", page_text, re.I)
        desc_m = re.search(r"Description[:\s]*([^:\n]+?)(?=Contractor|Quantity|Awarded Sum|$)", page_text, re.I)

        return {
            "contractor": contractor_m.group(1).strip() if contractor_m else "N/A",
            "contractor_address": address_m.group(1).strip() if address_m else "N/A",
            "awarded_sum": sum_m.group(1).strip() if sum_m else "N/A",
            "description": desc_m.group(1).strip() if desc_m else "N/A"
        }

    async def execute_pipeline(self, output_filename="gov_cedd.json"):
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            # 1. Crawl Stage 1 Index Page
            print(f"[*] Crawling Index Page via Crawl4AI: {self.base_url}")
            index_result = await crawler.arun(url=self.base_url, config=self.run_config)

            if not index_result.success:
                print(f"[-] Failed to crawl index page: {index_result.error_message}")
                return

            index_records = self.parse_index_table(index_result.cleaned_html or index_result.html)
            print(f"[+] Extracted {len(index_records)} contract rows from Index.")

            # 2. Open JSON file for writing JSON Lines
            with open(output_filename, "a", encoding="utf-8") as f:
                for idx, item in enumerate(index_records, start=1):
                    print(f"[*] Processing {idx}/{len(index_records)}: {item['contract_no']}")

                    detail_data = {}
                    if item["detail_url"]:
                        # Crawl Stage 2 Detail Page
                        detail_result = await crawler.arun(url=item["detail_url"], config=self.run_config)
                        if detail_result.success:
                            detail_data = self.parse_detail_html(detail_result.cleaned_html or detail_result.html)

                    # 3. Construct dictionary record with required tags
                    record = {
                        "department": "cedd",
                        "type": "contract_awarded",
                        "contract_no": item["contract_no"],
                        "subject": item["subject"],
                        "awarded_date": item["awarded_date"],
                        "contractor": detail_data.get("contractor", "N/A"),
                        "contractor_address": detail_data.get("contractor_address", "N/A"),
                        "awarded_sum": detail_data.get("awarded_sum", "N/A"),
                        "description": detail_data.get("description", "N/A"),
                        "detail_url": item["detail_url"]
                    }

                    # 4. Save each record as a separate line in JSON format
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    await asyncio.sleep(0.5)

            print(f"[✓] Saved all records to '{output_filename}'")

# Run Crawl4AI Pipeline
if __name__ == "__main__":
    extractor = Crawl4AICEDDExtractor()
    asyncio.run(extractor.execute_pipeline())