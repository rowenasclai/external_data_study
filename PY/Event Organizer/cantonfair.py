import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json
import pandas as pd

import datetime

# Get current date and time
current_dateTime = datetime.datetime.now()

# Print the result
print(current_dateTime)
# Example Output: 2026-03-16 22:32:00.123456



#url="https://asiamold-china.cn.messefrankfurt.com/guangzhou/en/exhibitor-search.html?page=2&pagesize=90"
#url="https://intertextile-shanghai-apparel-fabrics-spring.hk.messefrankfurt.com/shanghai/en/exhibitor-search.html?page=1&pagesize=30"
#url="https://365.cantonfair.org.cn/en-US/search?queryType=1&fCategoryId=461147892543934464&categoryId=461147892543934464"
url="https://365.cantonfair.org.cn/en-US/search?queryType=1&fCategoryId=461147245295706112&categoryId=732455405862752256"
#df = pd.read_json('/Users/rowena/Other Projects/external_data_study/Result/inhorgenta/inhorgenta.json', orient='records', lines=True)


def run(playwright1: Playwright) -> None:

    # browser = playwright.chromium.launch(headless=False)
    # # browser1 = playwright.chromium.launch(headless=False)
    # # browser2 = playwright.chromium.launch(headless=False)
    # # browser3 = playwright.chromium.launch(headless=False)
    # # browser4 = playwright.chromium.launch(headless=False)
    # # browser5 = playwright.chromium.launch(headless=False)
    # # browser6 = playwright.chromium.launch(headless=False)
    # # browser7 = playwright.chromium.launch(headless=False)
    # # browser8 = playwright.chromium.launch(headless=False)
    # # browser9 = playwright.chromium.launch(headless=False)
    # # browser10 = playwright.chromium.launch(headless=False)
    
    # context = browser.new_context()
    # page = context.new_page()
    # page.goto(url, wait_until="domcontentloaded")
    
    # page.get_by_text("click here").first.click()
    # page.locator("#app").get_by_text("Suppliers").click()

    # page.wait_for_load_state('networkidle')

    # page.get_by_role("button", name="Household Electrical").click()

    subpage=['Other Consumer Electronics and Information Products','Household audio video equipment','Other consumer electronics','Power products','Portable audio equipment','LED electronic products','Communication facilities','Computer Components','Communication cables','Smart Life','Computer peripherals','Mobile phone, telephone and other communication terminals','Computer accessories','Service Robots','Electronic health products','Computer entertainment equipment','Personal communication Products','Game and accessories','Other information products','Camera and accessories','Satellite communication equipment','Computer network equipment','Computer software','Drones']

    subpage_cnt=[15,8,6,4,4,3,3,3,3,3,2,2,2,2,1,1,1,1,1,1,1,1,1,1 ]

    for l in range(2,len(subpage)):
        browser = playwright.chromium.launch(headless=False)
    # browser1 = playwright.chromium.launch(headless=False)
    # browser2 = playwright.chromium.launch(headless=False)
    # browser3 = playwright.chromium.launch(headless=False)
    # browser4 = playwright.chromium.launch(headless=False)
    # browser5 = playwright.chromium.launch(headless=False)
    # browser6 = playwright.chromium.launch(headless=False)
    # browser7 = playwright.chromium.launch(headless=False)
    # browser8 = playwright.chromium.launch(headless=False)
    # browser9 = playwright.chromium.launch(headless=False)
    # browser10 = playwright.chromium.launch(headless=False)
    
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
    
        page.get_by_text("click here").first.click()
        page.locator("#app").get_by_text("Suppliers").click()

        page.wait_for_load_state('networkidle')

        page.get_by_role("button", name="Consumer Electronics and Information Products").click()
        
        #page.get_by_role("button", name="Household Electrical").click()
        page.get_by_text(f"{subpage[l]}", exact=True).click()

        page.wait_for_load_state('networkidle')

        all_list=page.locator(".sumec-exhibiting-shop-item-vertical")
        all_co=all_list.locator(".sumec-exhibiting-shop-item-vertical-title.text-ellipsis-1")

        end_item=''
        end_item1=''
        data={}
        print(f"{subpage[l]}")
        page1 = context.new_page()
    # page2= context.new_page()
    # page3 = context.new_page()
    # page4 = context.new_page()
    # page5 = context.new_page()
    # page6 = context.new_page()
    # page7 = context.new_page()
    # page8 = context.new_page()
    # page9 = context.new_page()
    # page10 = context.new_page()

    # Explicitly wait for the element to become visible

    
    # while page.get_by_role("listitem", name="page 20").is_visible()==False:
    #     page.get_by_role("listitem", name="Next 5 pages").click()
    #     page.wait_for_load_state('networkidle')
    #     page.wait_for_timeout(1000)

    # if page.get_by_role("listitem", name="page 20").is_visible()==True:
    #     page.get_by_role("listitem", name="page 20").click()


    #page.get_by_role("button", name="Household Electrical").click()
    #page.get_by_text("Small household appliances").click()
        length=subpage_cnt[l]
        for j in range(1,length):
        #for k in range(1,10):
            page.wait_for_load_state('networkidle')

            all_list1=page.locator(".sumec-exhibiting-shop-item-vertical")
            all_co1=all_list1.locator(".sumec-exhibiting-shop-item-vertical-title.text-ellipsis-1")
            start_item1=all_co1.nth(0).inner_text()

            while end_item1 ==start_item1:
    # #If it's still the same, wait a tiny bit longer or retry the click
                page.wait_for_timeout(1000)
                check_list1=page.locator(".sumec-exhibiting-shop-item-vertical")
                check1=check_list.locator(".sumec-exhibiting-shop-item-vertical-title.text-ellipsis-1")
                start_item1 = check1.nth(0).inner_text()

            current_dateTime = datetime.datetime.now()

            print('Processing Page '+str(j)+' '+current_dateTime.strftime("%Y-%m-%d %H:%M:%S"))

            browser1 = playwright.chromium.launch(headless=False)
            context1 = browser1.new_context()
        
            for i in range(all_co1.count()):
                test1=all_co1.nth(i).inner_text()
                data['Company_Name']=test1

                page1 = context1.new_page()

                try:
                    if page.get_by_text(f"{test1}").count()>0:
                        with page.expect_popup() as page1_info:
                            page.get_by_text(f"{test1}").first.click()
    
                        page1 = page1_info.value
                        data['URL']=page1.url

                    # context1.close()
                    # browser1.close()

                except:
                    pass

                page1.close()

                data['Category']='Consumer Electronics and Information Products'
                data['SubCategory']=subpage[l]
                with open('cantonfair.json', "a") as f:
                    json_record = json.dumps(data)
                    f.write(json_record + '\n') 
        
            context1.close()
            browser1.close()
        
            current_dateTime = datetime.datetime.now()

            print('Finish Processing Page '+str(j)+' '+current_dateTime.strftime("%Y-%m-%d %H:%M:%S"))

    #         #print(page1.url)
            end_item1=start_item1

            if j<length:
                page.get_by_role("button", name="Go to next page").click()
            j+=1

        context.close()
        browser.close()  
        

    

with sync_playwright() as playwright:
    run(playwright)