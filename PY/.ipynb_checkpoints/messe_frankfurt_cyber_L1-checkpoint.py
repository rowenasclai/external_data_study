import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json
import pandas as pd


#url="https://www.beautyworldtaipei.com/m/company_list.aspx?eid=BWT2026"
#url="https://www.beautyworldtaipei.com/m/company_list.aspx?eid=BWT2026&f=&c=&kw="

df=pd.read_csv('/Users/rowena/Other Projects/external_data_study/Result/Messe_Frankfurt/Secutech/messe_secutech_tw.csv')

df=df[df['co name'].isna()==False]


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    #print(df.loc[1,'url'])

    #print(len(df))

    data={}

    for i in range(len(df)):
        url=df.loc[i,'full_url']
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    #page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    # scroll_to_bottom(page)

        all_item=page.locator(".aem_table")
        data['url']=url
        data['all_info']=all_item.inner_text().split('\n')

        with open('tw_secutech_L1.json', "a") as f:
            json_record = json.dumps(data)
            f.write(json_record + '\n')  

    
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)