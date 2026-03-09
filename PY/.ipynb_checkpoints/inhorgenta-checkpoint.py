import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json
import pandas as pd


#url="https://asiamold-china.cn.messefrankfurt.com/guangzhou/en/exhibitor-search.html?page=2&pagesize=90"
#url="https://intertextile-shanghai-apparel-fabrics-spring.hk.messefrankfurt.com/shanghai/en/exhibitor-search.html?page=1&pagesize=30"
url="https://exhibitors.inhorgenta.com/exhibitordirectory/2026/list-of-exhibitors/"
df = pd.read_json('/Users/rowena/Other Projects/external_data_study/Result/inhorgenta/inhorgenta.json', orient='records', lines=True)


def run(playwright1: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page1 = context.new_page()

    page1.goto(url, wait_until="domcontentloaded")

    page1.get_by_role("button", name="Accept All").click()
    page1.get_by_role("button", name="Alphabet Filter - all").click()
    page1.get_by_role("button", name="60 per page").click()
    page1.wait_for_load_state('networkidle')
    
    old_name=''
    for j in range(1,16):
        page1.get_by_role("button", name="60 per page").click()
        page1.get_by_role("navigation", name="List-Navigtion").get_by_label("Enter page number").click()
        page1.get_by_role("navigation", name="List-Navigtion").get_by_label("Enter page number").fill(str(j))
        page1.get_by_role("navigation", name="List-Navigtion").get_by_label("Enter page number").press("Enter")

        if range==1:
            old_name=''

        page1.wait_for_selector(".mo_content", state="visible")

# 3. Double check the text isn't the old one
        new_name = page1.locator(".ce_head").nth(2).first.inner_text()
        
        while new_name == old_name:
    # If it's still the same, wait a tiny bit longer or retry the click
            page1.wait_for_timeout(1000)
            head=page1.locator(".ce_head")
            new_name = page1.locator(".ce_head").nth(2).first.inner_text()
            #print('wait')

        else:
            head=page1.locator(".ce_head")
            old_name=new_name
            #print('start')
            
        #old_name=page1.locator('.ce_head').last.inner_text()

        #print(head.all_inner_texts()[2])

        #print("processing page "+str(j))
        
        for i in range(head.count()-1):
            data={}
            data['co_name']=page1.locator(".ce_head").nth(i).inner_text()
            data['co_cnt']=page1.locator(".ce_cntnt").nth(i).inner_text()

            if page1.locator(".ce_head").nth(i).get_by_role("link", name=data['co_name']).count()>0:
                data['url']=page1.locator(".ce_head").nth(i).get_by_role("link", name=data['co_name']).get_attribute("href")
        
            if page1.locator(".ce_text").nth(i).count()>0:
                data['co_desc']=page1.locator(".ce_text").nth(i).inner_text()
            else:
                data['co_desc']=''
            if page1.locator(".ce_boothNo").nth(i).count()>0:
                data['co_booth']=page1.locator(".ce_boothNo").nth(i).inner_text()
            else:
                data['co_booth']=''
                
            with open('inhorgenta.json', "a") as f:
                json_record = json.dumps(data)
                f.write(json_record + '\n')  
            if i==2:
                print(data['co_name'])
        

    context.close()
    browser.close()


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page1 = context.new_page()
    for i in range(5):
        if pd.isna(df.loc[i,'url'])==False:
            page1.goto(df.loc[i,'url'], wait_until="domcontentloaded")
            if page1.get_by_role("button", name="Accept All").count()>0:
                page1.get_by_role("button", name="Accept All").click()
            test=page1.locator(".ce_cntnt")

            print(test.locator.last(".ce_cntnt1").inner_text())

            #".ce_cntnt > .ce_cntnt1 > .ce_head"

            #print(test.last.inner_text())

with sync_playwright() as playwright:
    run(playwright)