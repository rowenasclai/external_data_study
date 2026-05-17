import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json

# page.goto("https://www.messefrankfurt.com/frankfurt/en/event-search.html")
# page.locator(".m-search-result-item--event").first.click(button="right")
# page.get_by_role("button", name="E", exact=True).click()
# page.get_by_role("button", name="10").click()

url="https://www.messefrankfurt.com/frankfurt/en/event-search.html"

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page1 = context.new_page()
    page1.goto(url, wait_until="domcontentloaded")

    #exhibitor_list=page1.locator(".ex-exhibitor-search-results-container")
    exhibitor_list=page1.locator(".m-search-result-item--event")
    #count=exhibitor_list.locator(".ex-event-search-result-item__date-container").count()

    #page.locator(".m-search-result-item--event").first.click()
    #count1=page1.locator(".ex-event-search-results > div")
    #count1=exhibitor_list.locator("> div").count()
    #print(count1.count())

    data={}

    for j in range(1,11):
        for i in range(25):
            item_list=exhibitor_list.locator(".ex-event-search-result-item__headline").nth(i)
            item_date=exhibitor_list.locator(".ex-event-search-result-item__date-container").nth(i) 
            item_city=exhibitor_list.locator(".ex-event-search-result-item__location-city").nth(i)
            item_ctry=exhibitor_list.locator(".ex-event-search-result-item__location-country").nth(i)
            item_desc=exhibitor_list.locator(".ex-event-search-result-item__copy").nth(i)
            item_add_desc=exhibitor_list.locator(".ex-event-search-result-item__additional-location").nth(i)

            if exhibitor_list.get_by_role('link',name=item_list.inner_text(),exact=True).count()>0:
                item_url=exhibitor_list.get_by_role('link',name=item_list.inner_text(),exact=True).first.get_attribute('href')
            else:
                item_url='N/A'

            data['Event Title']=item_list.inner_text()
            data['Event Date']=item_date.inner_text()
            data['Event City']=item_city.inner_text()
            data['Event Country']=item_ctry.inner_text()
            data['Event Description']=item_desc.inner_text()
            data['Event More Description']=item_add_desc.inner_text()
            data['Event URL']=item_url

            #print(data)

            with open('messe_frankfurt_control.json', "a") as f:
                json_record = json.dumps(data)
                f.write(json_record + '\n')
        if j<10:
            page1.get_by_role("button", name=str(j+1)).click()
        #page1.get_by_role("button", name="E", exact=True).click()

    # itme=exhibitor_list.locator("div.m-search-result-item.ex-exhibitor-search-result-item.ex-exhibitor-search-result-item__grid.ex-exhibitor-search-result-item__inner")
    #item=item_date.nth(0)

    # print(item_list.inner_text())
    # print(item_date.inner_text())
    # print(item_city.inner_text())
    # print(item_ctry.inner_text())
    # print(item_desc.inner_text())
    # print(item_add_desc.inner_text())
    # print(item_url)


    #context.close()
    #browser.close()


with sync_playwright() as playwright:
    run(playwright)