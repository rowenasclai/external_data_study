"""
Web scraper for CPHI exhibitors using Playwright.
Extracts exhibitor information from https://exhibitors.cphi.com/cpch26/
with automatic pagination through "show more results" button.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Browser, Page
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CPHIExhibitorScraper:
    """Scraper for CPHI exhibition exhibitors."""
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        """
        Initialize the scraper.
        
        Args:
            headless: Run browser in headless mode (default: False - show browser)
            timeout: Page load timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.base_url = "https://exhibitors.cphi.com/cpch26/"
        #self.base_url = "https://www.interzoo.com/en/exhibitors-products/find-exhibitors"
        #self.base_url ="https://www.interzoo.com/en/exhibitors-products/find-exhibitors?state%5Bmenu%5D%5BfilterAZ%5D=Z"
        
    def initialize(self):
        """Initialize the browser."""
        try:
            self.playwright = sync_playwright().start()
            #self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.browser = self.playwright.chromium.launch(headless=False)
            logger.info(f"Browser initialized successfully (headless={self.headless})")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise
    
    def close(self):
        """Close the browser and playwright instance."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")
    
    def navigate_to_page(self):
        """Navigate to the CPHI exhibitors page."""
        try:
            self.page = self.browser.new_page()
            self.page.set_default_timeout(self.timeout)
            logger.info(f"Navigating to {self.base_url}")
            #self.page.goto(self.base_url)
            #self.page.goto(self.base_url, wait_until="networkidle")
            self.page.goto(self.base_url, wait_until="domcontentloaded")
            #self.page.locator("#transcend-consent-manager").click()
            #self.page.get_by_role("button", name="Accept all").click()
            #self.page.get_by_role("button", name="Allow all services").click()
            #self.page.get_by_test_id("view-switch-list-view").click()
            logger.info("Page loaded successfully")
        except Exception as e:
            logger.error(f"Failed to navigate to page: {e}")
            raise
    
    def wait_for_content(self):
        """Wait for main content to load."""
        try:
            # Wait for the main content area to load
            self.page.wait_for_selector("body", timeout=self.timeout)
            # Additional wait for dynamic content
            self.page.wait_for_load_state("networkidle")
            logger.info("Content loaded")
        except Exception as e:
            logger.warning(f"Timeout waiting for content: {e}")
    
    def scroll_to_element(self, element):
        """Scroll a specific element into view."""
        try:
            logger.info("Scrolling element into view...")
            self.page.evaluate("""
                arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
            """, element.element_handle())
            time.sleep(2)  # Wait for smooth scroll to complete
        except Exception as e:
            logger.warning(f"Error scrolling element into view: {e}")
    
    def click_show_more_until_done(self):
        """
        Click the 'show more results' button repeatedly until it disappears.
        Scrolls to element after each click to ensure new content is visible.
        """
        try:
            max_attempts = 200  # Prevent infinite loops
            attempt = 0
            
            while attempt < max_attempts:
                # Try different possible selectors for "show more" button
                show_more_selectors = [
                    "button:has-text('Show More Results')",
                    "button:has-text('Show More')",
                    "button:has-text('show more results')",
                    "button:has-text('show more')",
                    "[class*='show-more'] button",
                    "[class*='load-more'] button",
                    "button:has-text('Load More')",
                    "button:has-text('load more')",
                    ".show-more-btn",
                    ".load-more-btn",
                    ".view-more-btn",
                    "[data-action='show-more']",
                    "button[class*='more']",
                ]
                
                show_more_button = None
                selector_used = None
                
                # Try each selector
                for selector in show_more_selectors:
                    try:
                        show_more_button = self.page.query_selector(selector)
                        if show_more_button and show_more_button.is_visible():
                            selector_used = selector
                            logger.info(f"Found 'show more' button with selector: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                # If no button found, we're done
                if not show_more_button or not show_more_button.is_visible():
                    logger.info(f"No more 'show more' buttons found after {attempt} clicks")
                    break

                self.page.keyboard.press("End")
                # Scroll the button into view (center of screen)
                
                # Click the button
                logger.info(f"Clicking 'show more results' button (attempt {attempt + 1})")
                try:
                    #show_more_button.click()
                    #self.page.get_by_test_id("search-result-list").get_by_role("button", name="Show more arrow_forward_ios").click()
                    page.get_by_role("link", name="Show more results").click()
                except Exception as e:
                    logger.warning(f"Click failed, retrying with JavaScript: {e}")
                    
                    try:
                        self.page.evaluate(f"document.querySelectorAll('{selector_used}')[0].click()")
                    except Exception as e2:
                        logger.error(f"JavaScript click also failed: {e2}")
                        break
                
                # Wait for content to load
                logger.info("Waiting for new content to load...")
                self.page.wait_for_load_state("networkidle")
                
                # Add delay to ensure DOM updates
                time.sleep(2)
                
                attempt += 1
            
            if attempt >= max_attempts:
                logger.warning(f"Reached maximum attempts ({max_attempts}) for clicking 'show more'")
            else:
                logger.info(f"Successfully loaded all exhibitors after {attempt} clicks")
                
        except Exception as e:
            logger.error(f"Error clicking show more button: {e}")
    
    def get_exhibitors(self) -> List[Dict]:
        """
        Extract exhibitor information from the page.
        
        Returns:
            List of dictionaries containing exhibitor data
        """
        try:
            exhibitors = []
            
            # Get all exhibitor cards/elements - adjust selectors based on CPHI structure
            exhibitor_selectors = [
                "[class*='exhibitor']",
                "[class*='vendor']",
                "[class*='company']",
                "[data-exhibitor]",
                ".exhibitor-card",
                ".vendor-card",
                ".company-card",
                "div[class*='exhibit']",
                "div[class*='col-span-8 dm:col-span-4']",
                "div[class*='mt-3']",
                "div[class*='col-span-6 dm:col-span-8 dm:mt-1 mt-1']",
                "div[class*='grid grid-cols-6 gap-x-2 t:gap-x-4 dm:grid-cols-12 relative w-full items-center pr-[50px] dm:grid-cols-8']",
                "div[class*='exhibitors-list docu-filter-results']"
                
            ]
            
            exhibitor_elements = []
            for selector in exhibitor_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    if elements:
                        exhibitor_elements = elements
                        logger.info(f"Found {len(elements)} exhibitor elements using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not exhibitor_elements:
                logger.warning("No exhibitor elements found with standard selectors")
                # Inspect page structure
                logger.info("Page content length: " + str(len(self.page.content())))
                return exhibitors
            
            logger.info(f"Found {len(exhibitor_elements)} exhibitor elements")
            
            for i, element in enumerate(exhibitor_elements):
                try:
                    exhibitor_data = self._extract_exhibitor_data(element, i)
                    if exhibitor_data:
                        exhibitors.append(exhibitor_data)
                except Exception as e:
                    logger.warning(f"Error extracting exhibitor {i}: {e}")
                    continue
            
            return exhibitors
        except Exception as e:
            logger.error(f"Error getting exhibitors: {e}")
            return []
    
    def _extract_exhibitor_data(self, element, index: int) -> Optional[Dict]:
        """
        Extract data from a single exhibitor element.
        
        Args:
            element: The exhibitor element
            index: Index of the element
            
        Returns:
            Dictionary with exhibitor data or None
        """
        try:
            exhibitor = {
                "index": index,
                "name": None,
                "company_name": None,
                "description": None,
                "products": [],
                "location": None,
                "country": None,
                "contact": None,
                "email": None,
                "phone": None,
                "website": None,
                "booth": None,
                "scraped_at": datetime.now().isoformat()
            }
            
            # Try to extract company/exhibitor name
            name_selectors = [
                "[class*='name']",
                "[class*='title']",
                "h2", "h3", "h4",
                ".company-name",
                ".exhibitor-name",
                "[class*='company-name']",
                ".ais-Snippet-nonHighlighted",
                "[class*='ui_english']"
            ]
            
            for selector in name_selectors:
                try:
                    name_elem = element.query_selector(selector)
                    if name_elem:
                        text = name_elem.text_content()
                        if text and text.strip():
                            exhibitor["name"] = text.strip()
                            break
                except:
                    continue
            
            # Try to extract description
            desc_selectors = [
                "[class*='description']",
                "[class*='about']",
                "p",
                ".subtitle",
                "[class*='excerpt']",
                "div[class*='mt-2 w-full min-w-0 t:max-dm:ml-3 t:max-dm:mt-0']",
                "[class*='ui_chinese']"
            ]
            
            for selector in desc_selectors:
                try:
                    desc_elem = element.query_selector(selector)
                    if desc_elem:
                        text = desc_elem.text_content()
                        if text and text.strip() and not exhibitor["description"]:
                            exhibitor["description"] = text.strip()
                            break
                except:
                    continue
            
            # Try to extract location/country
            location_selectors = [
                "[class*='location']",
                "[class*='country']",
                "[class*='address']",
                ".location",
                ".country",
                "ul:nth-of-type(2)",
                "div[class*='exhibitor__country']"
            ]
            
            for selector in location_selectors:
                try:
                    #loc_elem = element.query_selector(selector)
                    loc_elem = element.query_selector(selector)
                    if loc_elem:
                        text = loc_elem.text_content()
                        if text and text.strip():
                            exhibitor["location"] = text.strip()
                            break
                except:
                    continue
            
            # Try to extract contact information
            try:
                email_elem = element.query_selector("[class*='email'], a[href*='mailto']")
                if email_elem:
                    email = email_elem.get_attribute("href") or email_elem.text_content()
                    exhibitor["email"] = email.replace("mailto:", "").strip() if email else None
            except:
                pass
            
            try:
                phone_elem = element.query_selector("[class*='phone'], a[href*='tel']")
                if phone_elem:
                    phone = phone_elem.get_attribute("href") or phone_elem.text_content()
                    exhibitor["phone"] = phone.replace("tel:", "").strip() if phone else None
            except:
                pass
            
            # Try to extract website/link
            try:
                #link_elem = element.query_selector("a[href^="/"]")
                link_elem = element.query_selector("[class*='without-default-icons flex w-full flex-col bg-module-background p-2 t:p-3 t:max-dm:flex-row dm:h-full']")
                if link_elem:
                    href = link_elem.get_attribute("href")
                    if href and "mailto" not in href and "tel" not in href:
                        exhibitor["website"] = href
            except:
                pass
            
            # Try to extract booth number
            booth_selectors = [
                "[class*='booth']",
                ".booth",
                "[class*='stand']",
                #".your-class-name ul",
                "[class*='subheadline copy-s ml-[-1rem] mt-2 flex w-fit flex-wrap gap-y-1 text-font dm:mt-1 [&_li]:w-fit [&_li]:border-r-[1px] [&_li]:px-2']",
                "div[class*='m-tag__txt']"
            ]
            
            for selector in booth_selectors:
                try:
                    booth_elem = element.query_selector(selector)
                    if booth_elem:
                        text = booth_elem.text_content()
                        if text and text.strip():
                            exhibitor["booth"] = text.strip()
                            break
                except:
                    continue
            
            # Try to extract products
            try:
                product_elems = element.query_selector_all("[class*='product'], .product-item, [class*='category']")
                for prod_elem in product_elems:
                    product_text = prod_elem.text_content()
                    if product_text and product_text.strip():
                        exhibitor["products"].append(product_text.strip())
            except:
                pass
            
            return exhibitor if exhibitor["name"] else None
        except Exception as e:
            logger.warning(f"Error extracting data from exhibitor element: {e}")
            return None
    
    def apply_filters(self, filters: Dict[str, str] = None):
        """
        Apply filters to the search (if needed).
        
        Args:
            filters: Dictionary of filter names and values
        """
        if not filters:
            return
        
        try:
            for filter_name, filter_value in filters.items():
                logger.info(f"Applying filter: {filter_name} = {filter_value}")
                # Look for filter elements and apply them
                # This is a placeholder - adjust based on actual page structure
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
    
    def scrape(self, filters: Dict[str, str] = None) -> List[Dict]:
        """
        Main scraping method.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List of exhibitor data dictionaries
        """
        try:
            self.initialize()
            self.navigate_to_page()
            self.wait_for_content()
            
            if filters:
                self.apply_filters(filters)
            
            # Click show more until button disappears
            logger.info("Starting to load all exhibitors...")
            self.click_show_more_until_done()
            
            # Extract all exhibitors
            exhibitors = self.get_exhibitors()
            logger.info(f"Successfully scraped {len(exhibitors)} exhibitors")
            
            return exhibitors
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise
        finally:
            self.close()


def main():
    """Main execution function."""
    try:
        # Initialize scraper with headless=False to show the browser
        scraper = CPHIExhibitorScraper(headless=False)
        
        # Optionally apply filters
        filters = {
            # Add filters as needed
            # "category": "Pharmaceutical",
            # "country": "Germany"
        }
        
        # Scrape data
        exhibitors = scraper.scrape(filters=filters)
        
        # Save results to JSON
        output_file = Path("cphi_extraction.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(exhibitors, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_file}")
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"CPHI Exhibition Scraping Summary")
        print(f"{'='*60}")
        print(f"Total exhibitors found: {len(exhibitors)}")
        if exhibitors:
            print(f"\nFirst exhibitor:")
            print(json.dumps(exhibitors[0], indent=2, ensure_ascii=False))
            print(f"\n... and {len(exhibitors) - 1} more exhibitors")
        print(f"\nResults saved to: {output_file.absolute()}")
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
