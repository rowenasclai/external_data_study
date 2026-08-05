import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json

url="https://sportshow.com.vn/en/listexhibition-this-yr-2/page/12/?display=list"

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

    for j in range(1,30):
        url="https://sportshow.com.vn/en/listexhibition-this-yr-2/page/"+str(j)+"/?display=list"

        page.goto(url, wait_until="domcontentloaded", timeout=60000)

    #scroll_to_bottom(page)

        all_item=page.locator(".gh-type-list-item")

        data={}

        for i in range(all_item.count()):
            data['co_name']=all_item.nth(i).locator("h4").first.inner_text()
            data['hall']=all_item.nth(i).locator(".gh-type-list-item--hall").first.inner_text()
            data['url']=all_item.nth(i).locator(".gh-type-list-item--link").first.inner_text()
            
            try:
                data['email']=all_item.nth(i).locator(".gh-type-list-item--email").first.inner_text()
            except:
                data['email']=''
                pass
                
            data['cat']=all_item.nth(i).locator(".gh-type-list-item--cat").first.inner_text()

            with open('vietnam_sportsworld_v1.json', "a") as f:
                json_record = json.dumps(data)
                f.write(json_record + '\n')  


    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)

