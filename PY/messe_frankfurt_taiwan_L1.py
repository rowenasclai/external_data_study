import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json
import pandas as pd


#url="https://www.beautyworldtaipei.com/m/company_list.aspx?eid=BWT2026"
#url="https://www.beautyworldtaipei.com/m/company_list.aspx?eid=BWT2026&f=&c=&kw="

df=pd.read_csv('/Users/rowena/Other Projects/external_data_study/Result/Messe_Frankfurt/BeautyWorld_TW/messe_beautyworld_tw.csv')

df=df[df['co_name'].isna()==False]


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    #print(df.loc[1,'url'])

    #print(len(df))

    #page.goto(url, wait_until="domcontentloaded", timeout=60000)
    #page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    # scroll_to_bottom(page)

    # all_item=page.locator(".none_list")
    # list_box=all_item.locator(".list_box")
    # overall_count=list_box.count()

    data={}

    for i in range(1,len(df)+1):
        url='https://www.beautyworldtaipei.com/m/'+df.loc[i,'url']
        data['url']=url
        page.goto(data['url'],wait_until="domcontentloaded", timeout=60000)
        
        data['co_info']=page.locator(".left").inner_text()
        data['co_background']=page.locator(".right").inner_text()

        with open('beautyworld_taiwan_L1.json', "a") as f:
            json_record = json.dumps(data)
            f.write(json_record + '\n')  

    # for i in range(list_box.count()):
    #     data['co_name']=list_box.nth(i).locator(".title").first.inner_text()
    #     data['url']=list_box.nth(i).get_by_role("link", name=data['co_name']).first.get_attribute("href")

    #     #print(data['co_name'])
    # #     print(data['url'])

    #     try:
    #         data['booth']=list_box.nth(i).locator(".boot").first.inner_text()
    #     except:
    #         pass

    #     try:
    #         data['co_name - tc']=list_box.nth(i).locator(".title").nth(1).inner_text()
    #     except:
    #         pass

    #     with open('beautyworld_taiwan.json', "a") as f:
    #         json_record = json.dumps(data)
    #         f.write(json_record + '\n')  


   

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)