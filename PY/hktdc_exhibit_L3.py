import re
from playwright.sync_api import Playwright, sync_playwright, expect

import asyncio
import json
#from playwright.async_api import async_playwright

import pandas as pd
import os

domain='https://www.hktdc.com'

prefix=input('What is the prefix of your exhibition?')
os.chdir("/Users/rowena/Other Projects/external_data_study/Result/HKTDC/"+prefix) 
df2_L1=pd.read_csv('hktdc_'+prefix+'_L2.csv')

df2_L1['supplier_url']=df2_L1['supplier_url'].fillna('about:blank')

def scrape(page) -> None:

    data={}

    data['url']=page.url
    card_box=page.locator(".item.css-19axa4z")

    child_div_locator = card_box.locator("> div")

    # Use the count() method to get the number of matching elements
    count = child_div_locator.count()
    #print(count)

    for i in range(3,count+1):
        card_box1=page.locator(".item.css-19axa4z > div:nth-child("+str(i)+")")
        content=card_box1.inner_text().split('\n')

        if len(content)>=3:
            for m in range(1,len(content)):
                if content[m][-1:]==':':
                    col=content[m][:-1]
                    cnt=''
                elif content[m][-1:]!=':':
                    cnt=cnt+' '+content[m]
                    cnt=cnt.strip()
                    data[col]=cnt

    with open('hktdc_'+prefix+'_L3.json', "a") as f:
        json_record = json.dumps(data)
        f.write(json_record + '\n')

    # ---------------------
    #context.close()
    #browser.close()

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()

    j=0
    page0 = context.new_page()
    page0.goto(df2_L1['supplier_url'][0], wait_until="domcontentloaded")
    scrape(page0)

    page1 = context.new_page()
    page2 = context.new_page()
    page3 = context.new_page()
    page4 = context.new_page()
    page5 = context.new_page()
    page6 = context.new_page()
    page7 = context.new_page()
    page8 = context.new_page()
    page9 = context.new_page()
    page10 = context.new_page()
    page11 = context.new_page()
    page12 = context.new_page()
    page13 = context.new_page()
    page14 = context.new_page()
    page15 = context.new_page()
    page16 = context.new_page()
    page17 = context.new_page()
    page18 = context.new_page()
    page19 = context.new_page()
    page20 = context.new_page()



    l=int(len(df2_L1)/20)
    #for j in range(55,l+1,1):
    for j in range(0,l,1):
        print('Processing '+str(20*j+1)+' - '+str(20*j+20)+' out of '+str(len(df2_L1)+1))
        page1.goto(df2_L1['supplier_url'][20*j+1], wait_until="domcontentloaded")
        page2.goto(df2_L1['supplier_url'][20*j+2], wait_until="domcontentloaded")
        page3.goto(df2_L1['supplier_url'][20*j+3], wait_until="domcontentloaded")
        page4.goto(df2_L1['supplier_url'][20*j+4], wait_until="domcontentloaded")
        page5.goto(df2_L1['supplier_url'][20*j+5], wait_until="domcontentloaded")
        page6.goto(df2_L1['supplier_url'][20*j+6], wait_until="domcontentloaded")
        page7.goto(df2_L1['supplier_url'][20*j+7], wait_until="domcontentloaded")
        page8.goto(df2_L1['supplier_url'][20*j+8], wait_until="domcontentloaded")
        page9.goto(df2_L1['supplier_url'][20*j+9], wait_until="domcontentloaded")
        page10.goto(df2_L1['supplier_url'][20*j+10], wait_until="domcontentloaded")
        page11.goto(df2_L1['supplier_url'][20*j+11], wait_until="domcontentloaded")
        page12.goto(df2_L1['supplier_url'][20*j+12], wait_until="domcontentloaded")
        page13.goto(df2_L1['supplier_url'][20*j+13], wait_until="domcontentloaded")
        page14.goto(df2_L1['supplier_url'][20*j+14], wait_until="domcontentloaded")
        page15.goto(df2_L1['supplier_url'][20*j+15], wait_until="domcontentloaded")
        page16.goto(df2_L1['supplier_url'][20*j+16], wait_until="domcontentloaded")
        page17.goto(df2_L1['supplier_url'][20*j+17], wait_until="domcontentloaded")
        page18.goto(df2_L1['supplier_url'][20*j+18], wait_until="domcontentloaded")
        page19.goto(df2_L1['supplier_url'][20*j+19], wait_until="domcontentloaded")
        page20.goto(df2_L1['supplier_url'][20*j+20], wait_until="domcontentloaded")

        scrape(page1)
        scrape(page2)
        scrape(page3)
        scrape(page4)
        scrape(page5)
        scrape(page6)
        scrape(page7)
        scrape(page8)
        scrape(page9)
        scrape(page10)
        scrape(page11)
        scrape(page12)
        scrape(page13)
        scrape(page14)
        scrape(page15)
        scrape(page16)
        scrape(page17)
        scrape(page18)
        scrape(page19)
        scrape(page20)

    r=len(df2_L1) %20
    
    if r==0:
        f=20
        l=int(len(df2_L1)/20)-1
    else:
        f=r
        l=int(len(df2_L1)/20)

    for i in range(1,f,1):
        page1.goto(df2_L1['supplier_url'][20*l+i], wait_until="domcontentloaded")
        scrape(page1)
        #print(20*l+i)
        
    # ---------------------
    context.close()
    browser.close()
    

with sync_playwright() as playwright:
    run(playwright)