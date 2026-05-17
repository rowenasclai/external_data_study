import random
import time
import json

from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth

from playwright_stealth import Stealth as apply_stealth
url="https://www.ccmtshow.com/en/339/list.html"

def scrape_exhibitors_sync(url):
    # Use 'with' to ensure the playwright instance closes automatically
    with sync_playwright() as p:
        # Launch the browser
        # Set headless=False if you want to watch it work (useful for debugging)
        browser = p.chromium.launch(headless=False)
        
        # Define a realistic context
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        
        # Apply stealth to the page (Sync version)
        stealth = Stealth()

        stealth.apply_stealth_sync(context)
        
        #url = f"https://exhibitions.globalsources.com/exhibitors/HK/?source=HKSHP&page={page_number}"
        print(f"Sync Mode: Accessing {url}...")

        try:
            # Navigate
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Mimic human "thinking" time
            time.sleep(random.uniform(2.0, 5.0))
            
            # Check for blocking
            if "challenge" in page.url or "verify" in page.url:
                print("Anti-bot detected. Try changing your IP or User-Agent.")
                return

            data={}

            page.locator("iframe").content_frame.get_by_role("textbox", name="Select").click()
            page.locator("iframe").content_frame.get_by_text("2004/page").click()

            page.wait_for_load_state('networkidle')
    #table_locator=page.locator(".el-table__body")
            #table_locator=page.get_by_role('table').locator('.el-table__body')
            table_locator=page.locator('.el-table__body')
            table_locator.wait_for(state="visible", timeout=60000)
            # item=page.locator('div[class="w-100% bg-#fff b-rd-8 min-h-100 p-20"]')

            

                # data['all_info']=all1
                # data['url']=url

                # with open('global_sourcing.json', "a") as f:
                #     json_record = json.dumps(data)
                #     f.write(json_record + '\n') 

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_exhibitors_sync(url)
    #for j in range(1,2):
     #   scrape_exhibitors_sync(j)
            
#page.goto("https://exhibitions.globalsources.com/exhibitors/HK/?source=HKSHP")
    # page.get_by_role("button", name="Go to next page").click()
    # page.get_by_role("banner").locator("i").nth(1).click()
    # page.get_by_role("listitem", name="page 3").click()






