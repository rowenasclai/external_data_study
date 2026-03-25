import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json


url="https://www.beautyworldtaipei.com/m/company_list.aspx?eid=BWT2026"
#url="https://www.beautyworldtaipei.com/m/company_list.aspx?eid=BWT2026&f=&c=&kw="

def scroll_to_bottom(page):
    last_height = page.evaluate("document.body.scrollHeight")
    
    while True:
        # Scroll to the bottom of the page
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        # Wait for new content to load (adjust time as needed)
        page.wait_for_timeout(2000) 
        
        # Calculate new scroll height and compare with last scroll height
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    #page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    scroll_to_bottom(page)

    all_item=page.locator(".none_list")
    list_box=all_item.locator(".list_box")
    # overall_count=list_box.count()

    #co_title=list_box.first.locator(".title").first

    #print(list_box.count())

    #print(list_box.all_inner_texts())

    #print(list_box.all_text_contents())

    #print(list_box.first.locator(".title").first.inner_text())

    #print(list_box.all_text_contents())
    
    # print(list_box.first.inner_text())
    # print(list_box.first.get_by_role("link", name=co_title.inner_text()).first.get_attribute("href"))
    # print(list_box.count())

    data={}

    for i in range(list_box.count()):
        data['co_name']=list_box.nth(i).locator(".title").first.inner_text()
        data['url']=list_box.nth(i).get_by_role("link", name=data['co_name']).first.get_attribute("href")

        #print(data['co_name'])
    #     print(data['url'])

        try:
            data['booth']=list_box.nth(i).locator(".boot").first.inner_text()
        except:
            pass

        try:
            data['co_name - tc']=list_box.nth(i).locator(".title").nth(1).inner_text()
        except:
            pass

        with open('beautyworld_taiwan.json', "a") as f:
            json_record = json.dumps(data)
            f.write(json_record + '\n')  


   

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)