import logging
import os
import time

import pandas as pd
from playwright.sync_api import Playwright, sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URL = "https://exhibitors.inhorgenta.com/exhibitordirectory/2026/list-of-exhibitors/"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Result", "inhorgenta_exhibitors_2026.csv")


def extract_page_data(page1):
    """Extract exhibitor data from the current page."""
    head = page1.locator(".ce_head")
    count = head.count()
    records = []

    for i in range(count):
        data = {}
        try:
            data['co_name'] = page1.locator(".ce_head").nth(i).inner_text().strip()

            cntnt = page1.locator(".ce_cntnt").nth(i)
            raw_cntnt = cntnt.inner_text().strip()

            # Parse location and country from content block (city/postcode line, country line)
            lines = [ln.strip() for ln in raw_cntnt.splitlines() if ln.strip()]
            data['co_location'] = lines[0] if len(lines) > 0 else ''
            data['co_country'] = lines[1] if len(lines) > 1 else ''

            if page1.locator(".ce_head").nth(i).get_by_role("link", name=data['co_name']).count() > 0:
                data['url'] = page1.locator(".ce_head").nth(i).get_by_role("link", name=data['co_name']).get_attribute("href")
            else:
                data['url'] = ''

            if page1.locator(".ce_text").nth(i).count() > 0:
                data['co_desc'] = page1.locator(".ce_text").nth(i).inner_text().strip()
            else:
                data['co_desc'] = ''

            if page1.locator(".ce_boothNo").nth(i).count() > 0:
                data['co_booth'] = page1.locator(".ce_boothNo").nth(i).inner_text().strip()
            else:
                data['co_booth'] = ''

            records.append(data)
        except Exception as e:
            logger.warning(f"Error parsing exhibitor item {i}: {e}")
            continue

    return records


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page1 = context.new_page()

    logger.info("Navigating to exhibitor directory...")
    page1.goto(URL, wait_until="domcontentloaded")

    # Accept cookie consent if present
    try:
        page1.get_by_role("button", name="Accept All").click(timeout=5000)
        logger.info("Accepted cookie consent.")
    except Exception:
        logger.info("No cookie consent dialog found, continuing.")

    # Set 60 results per page
    try:
        page1.get_by_role("button", name="60 per page").click(timeout=5000)
        page1.wait_for_load_state('networkidle')
        logger.info("Set display to 60 per page.")
    except Exception:
        logger.info("Could not set 60 per page, using default.")

    all_records = []
    page_num = 1

    while True:
        logger.info(f"Scraping page {page_num}...")
        page1.wait_for_selector(".ce_head", state="visible", timeout=15000)

        records = extract_page_data(page1)
        logger.info(f"  Extracted {len(records)} exhibitors from page {page_num}.")
        all_records.extend(records)

        # Check for next page button
        next_btn = page1.locator(".paging_RightArrows_cell")
        if next_btn.count() > 0 and next_btn.first.is_visible():
            try:
                head_count = page1.locator(".ce_head").count()
                old_name = page1.locator(".ce_head").nth(0).inner_text().strip() if head_count > 0 else ''
                next_btn.first.click()
                page1.wait_for_load_state('networkidle')

                # Wait until the page content has changed
                for _ in range(10):
                    try:
                        new_name = page1.locator(".ce_head").nth(0).inner_text().strip()
                        if new_name != old_name:
                            break
                    except Exception:
                        pass
                    time.sleep(0.5)

                page_num += 1
            except Exception as e:
                logger.warning(f"Error navigating to next page: {e}")
                break
        else:
            logger.info("No more pages found.")
            break

    context.close()
    browser.close()

    if all_records:
        df = pd.DataFrame(all_records)
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')
        logger.info(f"Saved {len(df)} records to {OUTPUT_PATH}")
        print(df.head(10).to_string())
    else:
        logger.warning("No data extracted.")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
