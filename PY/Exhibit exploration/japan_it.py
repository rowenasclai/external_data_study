"""
Japan IT Week Spring 2026 - Exhibitor Directory Scraper

Scrapes exhibitor data from the Japan IT Week Spring 2026 directory:
https://www.japan-it.jp/spring/en-gb/search/2026/directory.html#/

This is an RX Global (formerly Reed Exhibitions) event platform.
The directory is a JavaScript-rendered SPA, so Playwright is used
for browser automation to load and extract exhibitor data.

Output: japan_it.json (line-delimited JSON)

Fields extracted per exhibitor:
- company_name: Name of the exhibiting company
- booth: Booth number / location
- description: Company or product description
- categories: Product categories or tags
- url: Link to the exhibitor's detail page
- website: Company website (if available from detail page)

Usage:
    python japan_it.py

Note: Before running, ensure compliance with the website's terms of use
and robots.txt. This script is intended for research/study purposes only.
"""

import re
import json
import time
import os

from playwright.sync_api import Playwright, sync_playwright

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
BASE_URL = "https://www.japan-it.jp/spring/en-gb/search/2026/directory.html#/"
OUTPUT_FILE = "japan_it.json"
OUTPUT_DETAIL_FILE = "japan_it_detail.json"
HEADLESS = False  # Set True for production / CI runs
TIMEOUT = 60000   # Page load timeout in milliseconds


def _dismiss_cookie_banner(page):
    """Dismiss cookie consent banner if present."""
    try:
        # RX Global sites commonly use these button patterns
        for label in ["Accept All", "Accept all", "Accept", "I Accept",
                       "Accept Cookies", "OK", "Agree"]:
            btn = page.get_by_role("button", name=label)
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(1000)
                return
    except Exception:
        pass


def _safe_text(locator):
    """Return inner text of a locator, or empty string on failure."""
    try:
        if locator.count() > 0:
            return locator.first.inner_text().strip()
    except Exception:
        pass
    return ""


def _safe_attr(locator, attr):
    """Return attribute value of a locator, or empty string on failure."""
    try:
        if locator.count() > 0:
            return locator.first.get_attribute(attr) or ""
    except Exception:
        pass
    return ""


def _write_record(filepath, data):
    """Append a single JSON record to the output file."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def scrape_directory(playwright: Playwright, output_dir=None):
    """
    Level 1 scrape: Extract exhibitor list from the directory.

    Navigates through all pages of the directory listing and extracts
    basic exhibitor information (name, booth, description, categories, URL).

    Args:
        playwright: Playwright instance
        output_dir: Optional directory for output files. Defaults to current dir.
    """
    output_path = os.path.join(output_dir, OUTPUT_FILE) if output_dir else OUTPUT_FILE

    browser = playwright.chromium.launch(headless=HEADLESS)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
    )
    page = context.new_page()

    try:
        print(f"Navigating to {BASE_URL} ...")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
        page.wait_for_load_state("networkidle")

        # Dismiss cookie / consent banners
        _dismiss_cookie_banner(page)

        # Wait for the directory listing to render
        # RX Global directories typically render cards in a container
        page.wait_for_timeout(3000)

        # ── Determine total pages ────────────────────────────────────
        # RX directories often show pagination at the bottom.
        # We try to detect the last page number; fall back to scrolling.
        page_num = 1
        has_next = True

        while has_next:
            print(f"Scraping page {page_num} ...")
            page.wait_for_timeout(2000)

            # ── Extract exhibitor cards ──────────────────────────────
            # RX Global directory cards are typically rendered as list items
            # or divs with exhibitor info. We try several common selectors.
            cards = page.locator(
                "[class*='exhibitor-card'], "
                "[class*='directory-card'], "
                "[class*='search-result'], "
                "[class*='ExhibitorCard'], "
                "[class*='result-item'], "
                "div[data-exhibitor-id]"
            )

            # Fallback: try locating by role or common list structures
            if cards.count() == 0:
                cards = page.locator("article, .card, .list-item")

            # If still nothing, try broader approach - get all links in the
            # main content area that look like exhibitor links
            if cards.count() == 0:
                print("  Using broad link-based extraction ...")
                links = page.locator(
                    "a[href*='exhibitor'], "
                    "a[href*='directory'], "
                    "a[href*='profile']"
                )
                for i in range(links.count()):
                    data = {}
                    link = links.nth(i)
                    data["company_name"] = _safe_text(link)
                    data["url"] = _safe_attr(link, "href")
                    if data["company_name"]:
                        _write_record(output_path, data)
                        if i < 3:
                            print(f"    {data['company_name']}")
            else:
                card_count = cards.count()
                print(f"  Found {card_count} exhibitor card(s)")

                for i in range(card_count):
                    card = cards.nth(i)
                    data = {}

                    # Company name - try common heading patterns
                    name_loc = card.locator(
                        "h2, h3, h4, "
                        "[class*='name'], "
                        "[class*='title'], "
                        "[class*='heading']"
                    )
                    data["company_name"] = _safe_text(name_loc)

                    # Booth number
                    booth_loc = card.locator(
                        "[class*='booth'], "
                        "[class*='stand'], "
                        "[class*='location']"
                    )
                    data["booth"] = _safe_text(booth_loc)

                    # Description
                    desc_loc = card.locator(
                        "[class*='description'], "
                        "[class*='summary'], "
                        "[class*='copy'], "
                        "p"
                    )
                    data["description"] = _safe_text(desc_loc)

                    # Categories / tags
                    cat_loc = card.locator(
                        "[class*='category'], "
                        "[class*='tag'], "
                        "[class*='sector']"
                    )
                    data["categories"] = _safe_text(cat_loc)

                    # URL to exhibitor detail page
                    link_loc = card.locator("a")
                    href = _safe_attr(link_loc, "href")
                    if href and not href.startswith("http"):
                        href = "https://www.japan-it.jp" + href
                    data["url"] = href

                    # Also capture raw text as fallback
                    try:
                        data["raw_text"] = card.inner_text().strip()
                    except Exception:
                        data["raw_text"] = ""

                    if data["company_name"] or data["raw_text"]:
                        _write_record(output_path, data)
                        if i < 3:
                            print(f"    {data.get('company_name', 'N/A')}")

            # ── Pagination: go to next page ──────────────────────────
            next_btn = page.locator(
                "button:has-text('Next'), "
                "a:has-text('Next'), "
                "[class*='next'], "
                "[aria-label*='next'], "
                "[aria-label*='Next']"
            )

            if next_btn.count() > 0 and next_btn.first.is_enabled():
                try:
                    next_btn.first.click()
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)
                    page_num += 1
                except Exception:
                    has_next = False
            else:
                has_next = False

        print(f"Directory scrape complete. Output: {output_path}")

    except Exception as e:
        print(f"Error during directory scrape: {e}")
    finally:
        context.close()
        browser.close()


def scrape_exhibitor_details(playwright: Playwright, input_file=None,
                             output_dir=None):
    """
    Level 2 scrape: Visit each exhibitor's detail page for more info.

    Reads URLs from the Level 1 JSON output and visits each exhibitor's
    page to extract additional details (contact info, website, etc.).

    Args:
        playwright: Playwright instance
        input_file: Path to L1 JSON. Defaults to OUTPUT_FILE.
        output_dir: Optional directory for output files.
    """
    input_path = input_file or OUTPUT_FILE
    output_path = (os.path.join(output_dir, OUTPUT_DETAIL_FILE)
                   if output_dir else OUTPUT_DETAIL_FILE)

    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        return

    # Read L1 records
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Found {len(records)} exhibitors to process for details.")

    browser = playwright.chromium.launch(headless=HEADLESS)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
    )
    page = context.new_page()

    try:
        for idx, record in enumerate(records):
            url = record.get("url", "")
            if not url:
                continue

            detail = {"company_name": record.get("company_name", "")}

            try:
                print(f"  [{idx + 1}/{len(records)}] {detail['company_name']}")
                page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                page.wait_for_timeout(2000)

                _dismiss_cookie_banner(page)

                # Extract contact information from detail page
                # Website
                website_loc = page.locator(
                    "a[href*='http']:has-text('website'), "
                    "a[href*='http']:has-text('Website'), "
                    "[class*='website'] a, "
                    "[class*='web'] a"
                )
                detail["website"] = _safe_attr(website_loc, "href")

                # Email
                email_loc = page.locator(
                    "a[href^='mailto:'], "
                    "[class*='email']"
                )
                detail["email"] = _safe_text(email_loc)

                # Phone
                phone_loc = page.locator(
                    "a[href^='tel:'], "
                    "[class*='phone'], "
                    "[class*='tel']"
                )
                detail["phone"] = _safe_text(phone_loc)

                # Address
                addr_loc = page.locator(
                    "[class*='address'], "
                    "[class*='location']"
                )
                detail["address"] = _safe_text(addr_loc)

                # Full description
                desc_loc = page.locator(
                    "[class*='description'], "
                    "[class*='about'], "
                    "[class*='profile-content'], "
                    "[class*='summary']"
                )
                detail["full_description"] = _safe_text(desc_loc)

                # Booth
                booth_loc = page.locator(
                    "[class*='booth'], "
                    "[class*='stand']"
                )
                detail["booth"] = _safe_text(booth_loc)

                detail["exhibitor_url"] = url

            except Exception as e:
                detail["error"] = str(e)

            _write_record(output_path, detail)

        print(f"Detail scrape complete. Output: {output_path}")

    except Exception as e:
        print(f"Error during detail scrape: {e}")
    finally:
        context.close()
        browser.close()


# ──────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Japan IT Week Spring 2026 - Exhibitor Directory Scraper")
    print("=" * 60)
    print()
    print(f"Target: {BASE_URL}")
    print(f"Output: {OUTPUT_FILE} (directory) / {OUTPUT_DETAIL_FILE} (details)")
    print()

    with sync_playwright() as playwright:
        # Level 1: Scrape exhibitor directory listing
        scrape_directory(playwright)

        # Level 2: Scrape individual exhibitor detail pages
        # Uncomment below to run after L1 is complete:
        # scrape_exhibitor_details(playwright)
