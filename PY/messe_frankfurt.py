import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json


#url="https://asiamold-china.cn.messefrankfurt.com/guangzhou/en/exhibitor-search.html?page=2&pagesize=90"
#url="https://intertextile-shanghai-apparel-fabrics-spring.hk.messefrankfurt.com/shanghai/en/exhibitor-search.html?page=1&pagesize=30"
#url="https://intertextile-shenzhen.hk.messefrankfurt.com/shenzhen/en/exhibitor-search.html?page=1&pagesize=30"

#url="https://ishc-cihe.hk.messefrankfurt.com/beijing/en/exhibitor-search.html?page=1&pagesize=30
#url="https://interpets.jp.messefrankfurt.com/tokyo/en/exhibitor-search.html?page=1&pagesize=30"
#url="https://shenzhen-international-toy-and-hobby-fair.hk.messefrankfurt.com/shenzhen/en/exhibitor-search.html?page=1&pagesize=30"
#url="https://shenzhen-international-stroller-mother-and-baby-product-fair.hk.messefrankfurt.com/shenzhen/en/exhibitor-search.html?page=1&pagesize=30"

#url="https://auto-maintenance.cn.messefrankfurt.com/beijing/en/exhibitor-search.html?page=1&pagesize=30"
#url="https://intertextile-shanghai-apparel-fabrics-spring.hk.messefrankfurt.com/shanghai/en/exhibitor-search.html?page=1&pagesize=30"

url="https://auto-maintenance.cn.messefrankfurt.com/beijing/en/exhibitor-search.html?page=1&pagesize=90"

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page1 = context.new_page()
    #page1.goto(url)

    data={}

    for j in range(1,17):
        #url="https://intertextile-shanghai-apparel-fabrics-spring.hk.messefrankfurt.com/shanghai/en/exhibitor-search.html?page="+str(j)+"&pagesize=30"
        url="https://auto-maintenance.cn.messefrankfurt.com/beijing/en/exhibitor-search.html?page="+str(j)+"&pagesize=90"

        page1.goto(url)

        for i in range(90):

            exhibitor_list=page1.locator(".ex-exhibitor-search-results-container")

            item=exhibitor_list.locator("div.m-search-result-item.ex-exhibitor-search-result-item.ex-exhibitor-search-result-item__grid.ex-exhibitor-search-result-item__inner").nth(i)

            data['company_name']=item.locator("h4.ex-exhibitor-search-result-item__headline").inner_text()

            data['description']=item.locator("p.ex-exhibitor-search-result-item__copy").inner_text()
            data['exhibit loc']=item.locator("div.ex-exhibitor-search-result-item__location").inner_text()

    #item_url_loc=exhibitor_list.locator("div.ex-exhibitor-search-results-container.ex-exhibitor-search-results-container--grid-cols.show-confair-container")

    #page.get_by_role("link", name="ARTOP MOLD INDUSTRIAL CO.,").click()
    #page.locator(".slick-slider.m-tab-slider__slider > .slick-list > .slick-track > .slick-slide.slick-active").click(button="right")
            if page1.get_by_role("link", name=data['company_name']).count()>1:
                data['url']=page1.get_by_role("link", name=data['company_name']).first.get_attribute("href")

            elif page1.get_by_role("link", name=data['company_name']).count()>0:
                data['url']=page1.get_by_role("link", name=data['company_name']).get_attribute("href")

            with open('beijing-automechanika.json', "a") as f:
                json_record = json.dumps(data)
                f.write(json_record + '\n')  

    
    #print(item.inner_text())
    #print(item_co.inner_text())
    #print(item_desc.inner_text())
    #print(item_loc.inner_text())
    #print(item_url)


    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)