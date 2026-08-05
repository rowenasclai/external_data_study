import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json

def scrape_30_pages_sync():
    base_url = "https://sportshow.com.vn/en/listexhibition-this-yr-2/page/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    records = []

    for page_num in range(1, 31):
        url = f"{base_url}{page_num}/?display=list"
        print(f"[*] Synchronously fetching page {page_num}/30...")

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find headers / titles containing company names
            for h in soup.find_all(["h2", "h3", "h4", "strong"]):
                page.goto("https://sportshow.com.vn/en/listexhibition-this-yr-2/page/12/?display=list")
                page.locator(".gh-type-list-item").first.click()
                page.locator(".gh-type-list-items > div:nth-child(2)").click()
                page.locator(".gh-type-list-item--hall").first.click()
                page.locator(".gh-type-list-item--link").first.click()

                gh-type-list-item--cat
                
                page.locator("b").first.click()
                
                name = h.get_text(strip=True)
                if name and len(name) > 3 and not any(w in name.lower() for w in ["search", "menu", "exhibition", "home"]):
                    records.append({
                        "page_number": page_num,
                        "company_name": name,
                        "exhibition_name": "Vietnam Sport Show 2026",
                        "source_url": url
                    })
            time.sleep(0.5)

        except Exception as e:
            print(f"    [-] Error on page {page_num}: {e}")

    df = pd.DataFrame(records).drop_duplicates(subset=["company_name"])
    df.to_csv("vietnam_sport_show_all_pages.csv", index=False, encoding="utf-8-sig")
    print(f"[✓] Saved {len(df)} records to 'vietnam_sport_show_all_pages.csv'")

if __name__ == "__main__":
    scrape_30_pages_sync()