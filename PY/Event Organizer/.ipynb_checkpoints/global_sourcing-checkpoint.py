import random
import time
import json

from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth

from playwright_stealth import Stealth as apply_stealth

page_number=2
def scrape_exhibitors_sync(page_number):
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
        #stealth_tool = Stealth() 
        
        # 2. Apply it to the page
        #stealth_tool.apply(page)
        #apply_stealth(page)
        #Stealth(page)

        stealth = Stealth()
        # navigator_languages_override=custom_languages,
        # init_scripts_only=True)

        stealth.apply_stealth_sync(context)
        
        url = f"https://exhibitions.globalsources.com/exhibitors/HK/?source=HKSHP&page={page_number}"
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
            item=page.locator('div[class="w-100% bg-#fff b-rd-8 min-h-100 p-20"]')
            title=item.locator(".line-clamp-2.a-def.transition-all-300").first
            url=item.get_by_role("link", name=f"{title.first.inner_text()}").get_attribute("href")

            #w-100% bg-#fff b-rd-8 min-h-100 p-20

            #print(item.nth(1).all_inner_texts())
            all1=item.first.inner_text().split('\n')
            data['all_info']=all1
            data['url']=url

            #print(data)

            with open('global_sourcing.json', "a") as f:
                json_record = json.dumps(data)
                f.write(json_record + '\n') 
            

            for i in range(1,item.count()):
                box=page.locator('div[class="w-100% bg-#fff b-rd-8 min-h-100 p-20"]').nth(i)

                all1=box.inner_text().split('\n')

                title=box.locator(".line-clamp-2.a-def.transition-all-300")
                # data['company name']=title.inner_text()

                # try:
                #     label=box.locator('div[class="mt-16 flex-ver flex-wrap gap-3 md:mt-12"]')
                # except:
                #     pass
                    
                # booth=box.locator(".truncate.lh-17")

                url=box.get_by_role("link", name=f"{title.inner_text()}").get_attribute("href")

                # data['label']=label.inner_text()
                # data['booth']=booth.inner_text()
                # data['url']=url

                data['all_info']=all1
                data['url']=url

                with open('global_sourcing.json', "a") as f:
                    json_record = json.dumps(data)
                    f.write(json_record + '\n') 

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    #scrape_exhibitors_sync(1)
    for j in range(1,2):
        scrape_exhibitors_sync(j)
            
#page.goto("https://exhibitions.globalsources.com/exhibitors/HK/?source=HKSHP")
    # page.get_by_role("button", name="Go to next page").click()
    # page.get_by_role("banner").locator("i").nth(1).click()
    # page.get_by_role("listitem", name="page 3").click()






