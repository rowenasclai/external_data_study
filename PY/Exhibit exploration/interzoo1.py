"""
Web scraper for Interzoo exhibitors using Playwright.
Extracts exhibitor and product information from https://www.interzoo.com/en/exhibitors-products/find-exhibitors
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


class InterzooScraper:
    """Scraper for Interzoo exhibitors and products."""
    
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
        self.base_url = "https://www.interzoo.com/en/exhibitors-products/find-exhibitors"
        
    def initialize(self):
        """Initialize the browser."""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
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
        """Navigate to the Interzoo exhibitors page."""
        try:
            self.page = self.browser.new_page()
            self.page.set_default_timeout(self.timeout)
            logger.info(f"Navigating to {self.base_url}")
            self.page.goto(self.base_url, wait_until="networkidle")
            self.page.get_by_role("button", name="Allow all services").click()
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
    
    def get_exhibitors(self) -> List[Dict]:
        """
        Extract exhibitor information from the page.
        
        Returns:
            List of dictionaries containing exhibitor data
        """
        try:
            exhibitors = []
            
            # Get all exhibitor cards/elements
            # Adjust selectors based on actual page structure
            exhibitor_elements = self.page.query_selector_all(
                "[data-exhibitor], .exhibitor, .exhibitor-item, [class*='col-span-8 dm:col-span-4']"
            )
            
            if not exhibitor_elements:
                logger.warning("No exhibitor elements found with standard selectors")
                # Try alternative approach - get page content for inspection
                content = self.page.content()
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
                "description": None,
                "products": [],
                "contact": None,
                "website": None,
                "scraped_at": datetime.now().isoformat()
            }
            
            # Try to extract name
            name_elem = element.query_selector("[class*='without-default-icons flex w-full flex-col bg-module-background p-2 t:p-3 t:max-dm:flex-row dm:h-full'], h2, h3, .title")
            if name_elem:
                exhibitor["name"] = name_elem.text_content()
                exhibitor["name"] = exhibitor["name"].strip() if exhibitor["name"] else None
            
            # Try to extract description
            desc_elem = element.query_selector("[class*='description'], p, .subtitle")
            if desc_elem:
                exhibitor["description"] = desc_elem.text_content()
                exhibitor["description"] = exhibitor["description"].strip() if exhibitor["description"] else None
            
            # Try to extract link
            link_elem = element.query_selector("a")
            if link_elem:
                exhibitor["website"] = link_elem.get_attribute("href")
            
            # Try to extract products
            product_elems = element.query_selector_all("[class*='product'], .product-item")
            for prod_elem in product_elems:
                product_text = prod_elem.text_content()
                if product_text:
                    exhibitor["products"].append(product_text.strip())
            
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
                pass
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
        scraper = InterzooScraper(headless=False)
        
        # Optionally apply filters
        filters = {
            # Add filters as needed
            # "product": "feed",
            # "country": "Germany"
        }
        
        # Scrape data
        exhibitors = scraper.scrape(filters=filters)
        
        # Save results to JSON
        output_file = Path("interzoo_exhibitors.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(exhibitors, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_file}")
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"Scraping Summary")
        print(f"{'='*50}")
        print(f"Total exhibitors found: {len(exhibitors)}")
        if exhibitors:
            print(f"\nFirst exhibitor:")
            print(json.dumps(exhibitors[0], indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
