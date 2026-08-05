import re
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import pandas as pd
from playwright.sync_api import sync_playwright
import json

def scrape_tairos_exhibitors(url: str = "https://tairos.chanchao.com.tw/en/VisitorExhibitor") -> pd.DataFrame:
    print(f"[*] Navigating to TAIROS 2026 Directory: {url}")
    
    # 1. Fetch rendered DOM using synchronous Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Navigate and wait for AJAX/XHR network requests to complete
        page.goto(url, wait_until="networkidle", timeout=45000)

        # Scroll to trigger lazy-loaded cards
        for _ in range(3):
            page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(1)

        html_content = page.content()
        browser.close()

    # 2. Parse DOM with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    records = []

    # Find all exhibitor detail page anchors matching Chan Chao's URL pattern
    detail_links = soup.find_all("a", href=lambda h: h and "/VisitorExhibitor/Detail" in h)

    for a in detail_links:
        company_name = a.get_text(strip=True)
        if not company_name or len(company_name) < 2:
            continue
        
        # Locate parent card container
        parent_card = a.find_parent(["div", "li", "tr"])
        card_text = parent_card.get_text(" ", strip=True) if parent_card else ""
        
        # Extract Booth Number using regex (e.g. "Booth No: M1136")
        booth_match = re.search(r"Booth\s*No[:\s]*([A-Z0-9\-\/]+)", card_text, re.IGNORECASE)
        booth_name = booth_match.group(1) if booth_match else "N/A"
        
        # Extract Country / Area
        country_match = re.search(r"Country[:\s]*([A-Za-z\s]+)", card_text, re.IGNORECASE)
        country = country_match.group(1).strip() if country_match else "Unspecified"

        full_detail_url = urljoin(url, a["href"])

        records.append({
            "exhibition_name": "TAIROS 2026 (Taiwan Automation Intelligence & Robot Show)",
            "company_name": company_name,
            "booth_name": booth_name,
            "country": country,
            "detail_url": full_detail_url
        })

    # Clean and deduplicate records by company name
    df = pd.DataFrame(records).drop_duplicates(subset=["company_name"])

    with open('tairos.json', "a") as f:
        json_record = json.dumps(records)
        f.write(json_record + '\n')  
    print(f"[+] Extracted {len(df)} exhibitor records from TAIROS 2026.")
    return df

if __name__ == "__main__":
    for i in range(1,44):
        tairos_url = "https://tairos.chanchao.com.tw/en/VisitorExhibitor?page="+str(i)
    
        df_tairos = scrape_tairos_exhibitors(tairos_url)
        print(df_tairos.head())
    
    # Save to CSV
        #df_tairos.to_csv("tairos_2026_exhibitors_v1.csv", index=False)
