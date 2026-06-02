import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json


url="https://www.secutech.com/26/en/exlist.aspx"

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(url,wait_until="domcontentloaded", timeout=60000)
    #page1.goto(url)



    # print(title.nth(9).inner_text().split('\n')[0])
    # print(title.nth(9).get_by_role("link", name=title.first.inner_text().split('\n')[0]).get_attribute("href"))
    # print(title.count())

    data={}

    for j in range(1,25):
        all_content=page.locator(".aem_box")
        title=all_content.locator(".aem_producttext.aem_column")
        
        for i in range(title.count()):
            data['co name']=title.nth(i).inner_text().split('\n')[0]
            data['Industry Category']=title.nth(i).inner_text().split('\n')[1]
            data['Country']=title.nth(i).inner_text().split('\n')[2]
            data['Booth']=title.nth(i).inner_text().split('\n')[3]

            try:
                data['url']=title.nth(i).get_by_role("link", name=title.nth(i).inner_text().split('\n')[0]).get_attribute("href")
            except:
                pass

            with open('tw_secutech.json', "a") as f:
                json_record = json.dumps(data)
                f.write(json_record + '\n') 

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        if j!=25:
            page.locator("[id=\"ctl00_cphMainContent_dd_pages2$ajaxdest\"]").click()

            n=j+1
            # This automatically triggers the 'change' event in 99% of cases
            page.select_option("#ctl00_cphMainContent_dd_pages2", value=f"{str(n)}")
            #page.select_option("#ctl00_cphMainContent_dd_pages2", value="{j}+1")
            #page.locator("[id=\"ctl00_cphMainContent_dd_pages2\"]").dispatch_event("change")
            #page.locator("#ctl00_cphMainContent_dd_pages2").select_option("2")
            #page.locator("[id=\"ctl00_cphMainContent_dd_pages2\"]").select_option('"f{j+1}"')
            
            

    #     page.goto("https://www.secutech.com/26/en/exlist.aspx")
    #     page.locator("#ctl00_cphMainContent_dd_pages2").select_option('"f{j}"')
    
    #     #url="https://intertextile-shanghai-apparel-fabrics-spring.hk.messefrankfurt.com/shanghai/en/exhibitor-search.html?page="+str(j)+"&pagesize=30"
    #     url="https://auto-maintenance.cn.messefrankfurt.com/beijing/en/exhibitor-search.html?page="+str(j)+"&pagesize=30"

    #     page1.goto(url)

    #     for i in range(30):

    #         exhibitor_list=page1.locator(".ex-exhibitor-search-results-container")

    #         item=exhibitor_list.locator("div.m-search-result-item.ex-exhibitor-search-result-item.ex-exhibitor-search-result-item__grid.ex-exhibitor-search-result-item__inner").nth(i)

    #         data['company_name']=item.locator("h4.ex-exhibitor-search-result-item__headline").inner_text()

    #         data['description']=item.locator("p.ex-exhibitor-search-result-item__copy").inner_text()
    #         data['exhibit loc']=item.locator("div.ex-exhibitor-search-result-item__location").inner_text()

    # #item_url_loc=exhibitor_list.locator("div.ex-exhibitor-search-results-container.ex-exhibitor-search-results-container--grid-cols.show-confair-container")

    # #page.get_by_role("link", name="ARTOP MOLD INDUSTRIAL CO.,").click()
    # #page.locator(".slick-slider.m-tab-slider__slider > .slick-list > .slick-track > .slick-slide.slick-active").click(button="right")
    #         if page1.get_by_role("link", name=data['company_name']).count()>1:
    #             data['url']=page1.get_by_role("link", name=data['company_name']).first.get_attribute("href")

    #         elif page1.get_by_role("link", name=data['company_name']).count()>0:
    #             data['url']=page1.get_by_role("link", name=data['company_name']).get_attribute("href")

    #         with open('bj_auto_maintenance.json', "a") as f:
    #             json_record = json.dumps(data)
    #             f.write(json_record + '\n')  

    
    #print(item.inner_text())
    #print(item_co.inner_text())
    #print(item_desc.inner_text())
    #print(item_loc.inner_text())
    #print(item_url)


    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)