import re
from playwright.sync_api import Playwright, sync_playwright, expect

from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth

from playwright_stealth import Stealth as apply_stealth
import csv

import asyncio
import json


url="https://www.ccmtshow.com/en/339/list.html"

def run(playwright: Playwright) -> None:

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    viewport={"width": 1920, "height": 1080},
    locale="en-US"
)
    
    stealth = Stealth()
        # navigator_languages_override=custom_languages,
        # init_scripts_only=True)
    page = context.new_page()
    stealth.apply_stealth_sync(context)


        
       

    page.goto(url, wait_until="domcontentloaded",timeout=300000)
    page.wait_for_load_state('networkidle')

    page.locator("iframe").content_frame.get_by_role("textbox", name="Select").click()
    page.locator("iframe").content_frame.get_by_text("2004/page").click()

    page.wait_for_load_state('networkidle')
    #table_locator=page.locator(".el-table__body")
    table_locator=page.get_by_role('table').locator('.el-table__body')
    table_locator.wait_for(state="visible", timeout=60000)
    #print(page.locator(".el-table__body").inner_text())


    # data={}

    # for i in range(2,2005):

    #     item=page.locator(".el-table__row").nth(i-1)
        

    #     data['company_name_tc']=item.locator(".el-table_1_column_2  ").inner_text()
    #     data['company_name_en']=item.locator(".el-table_1_column_3  ").inner_text()
    #     data['booth']=item.locator(".el-table_1_column_4  ").inner_text()

    #     if item.get_by_role("link", name='Exihibits').count()>1:
    #         data['url']=item.get_by_role("link", name='Exihibits').first.get_attribute("href")

    #     with open('Other Projects/external_data_study/PY/ccmts.json', "a") as f:
    #         json_record = json.dumps(data)
    #         f.write(json_record + '\n')  


    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)