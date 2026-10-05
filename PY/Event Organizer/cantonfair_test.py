import asyncio
from playwright.async_api import async_playwright
import json
import random

async def scrape_canton_fair():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        url=['https://365.cantonfair.org.cn/en-US/search?queryType=2&fCategoryId=461148003609088000&categoryId=461148003609088000&searchWord=']

        maincat=['Light & Electrical']

        subcat=['All']

        no_cnt=[119]

        for l in range(len(url)):
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = await context.new_page()

        # Navigate to the target page
            await page.goto(url[l], wait_until="networkidle")

            try:
                await page.get_by_role("button", name="click here").first.click()
            except:
                pass
        
            # Wait for the supplier items to render
            card_selector = ".sumec-exhibiting-shop-item-vertical--list"
            await page.wait_for_selector(card_selector)
        
            all_suppliers = []
        
            #while True:
        
            for i in range(2,int(no_cnt[l])):
                cards = await page.locator(card_selector).all()
                for card in cards:
                    # 1. Company Name
                    name_el = card.locator(".sumec-exhibiting-shop-item-vertical-title")
                    name = await name_el.get_attribute("title") if await name_el.count() > 0 else None
                    if not name:
                        name = (await name_el.inner_text()).strip() if await name_el.count() > 0 else "N/A"
        
                    # 2. Booth & Category details (active slide)
                    category_el = card.locator(".booth-area-title")
                    category = (await category_el.first.inner_text()).strip() if await category_el.count() > 0 else None
        
                    phase_el = card.locator(".booth-area-phase")
                    phase = (await phase_el.first.inner_text()).strip() if await phase_el.count() > 0 else None
        
                    booth_el = card.locator(".booth-area-number")
                    booth = (await booth_el.first.inner_text()).strip() if await booth_el.count() > 0 else None
        
                    # 3. Tags / Badges
                    tags = []
                    tag_imgs = await card.locator(".sumec-exhibiting-shop-item-tags img").all()
                    for img in tag_imgs:
                        badge_title = await img.get_attribute("title") or await img.get_attribute("alt")
                        if badge_title:
                            tags.append(badge_title.split("：")[0].strip())
        
                    # 4. Product Preview Image URLs
                    prod_imgs = await card.locator(".sumec-exhibiting-shop-item-vertical-product-item img").all()
                    product_image_urls = [await img.get_attribute("src") for img in prod_imgs if await img.get_attribute("src")]
                    
                    all_suppliers = []
                    all_suppliers.append({
                        "company_name": name,
                        "category": category,
                        "phase": phase,
                        "booth_number": booth,
                        "tags": tags,
                        "product_images": product_image_urls,
                        "Category": maincat[l],
                        "SubCategory": subcat[l]
                            
                    })
        
                #print(all_suppliers)
                    with open('cantonfair_2026_'+maincat[l]+'_'+subcat[l]+'.json', "a") as f:
                        json_record = json.dumps(all_suppliers)
                        f.write(json_record + '\n') 
                
                print(f"Scraped page {maincat[l]}: {subcat[l]} {i} {len(all_suppliers)} suppliers so far...")
        
                    #data['Category']='Gifts & Decorations'
                    
        
                # Check pagination
                #next_btn = page.locator(".sumec-exhibiting-search-pagination .btn-next")
                #next_btn=page.get_by_role("button", name="Go to next page")
                #page.get_by_role("button", name="click here").first.click()
                #page.get_by_role("img").nth(2).click()
                #page.get_by_text("Weaving, Rattan and Iron").click()
                #page.get_by_role("button", name="Go to next page").click()
                #is_disabled = await next_btn.get_attribute("disabled") or await next_btn.get_attribute("aria-disabled") == "true"
                
                #if is_disabled:
                    #break
        
                # Click next and wait for new items to update
                #await next_btn.click()
        
                #next_btn = page.get_by_role("button", name="Go to next page")
                #next_btn = page.get_by_role("button", name="2")

                try:
                    next_btn=page.get_by_role("listitem", name="page "+str(i), exact=True)
                    await next_btn.dispatch_event("click")
                    await page.wait_for_selector(card_selector)
                except:
                    pass
        
                    # or:
                    #await next_btn.evaluate("el => el.click()")
                    #await page.get_by_role("button", name="Go to next page").click()
                #await page.wait_for_timeout(2000)  # Brief delay to allow Vue DOM to re-
                delay = random.uniform(3.0, 6.0)
                await asyncio.sleep(delay)

            await browser.close()
        #return all_suppliers
        return

if __name__ == "__main__":
    suppliers = asyncio.run(scrape_canton_fair())
    #print(suppliers[:2])