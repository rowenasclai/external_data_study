import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

#import asyncio
import json

import os
#from playwright.async_api import async_playwright

#from concurrent.futures.thread import ThreadPoolExecutor

import pandas as pd

prefix=input('What is the prefix of your exhibition?')

os.chdir("/Users/rowena/Other Projects/external_data_study/Result/Exhibition Organizers/HKTDC/"+prefix) 
df2_L1=pd.read_csv('hktdc_'+prefix+'_L1.csv')
#df2_L1=pd.read_csv('hktdc_hkdgp_L1.csv')
domain='https://www.hktdc.com'

def scrape(page):
    df={}

    try:
        card_box=page.locator(".d-flex.flex-column.col-12")
        all_text=card_box.inner_text().split('\n')

    # Locate all direct child div elements using the child combinator (>)
    # The selector will be '#parent_div > div'
        child_div_locator = card_box.locator("> div")

    # Use the count() method to get the number of matching elements
        count = child_div_locator.count()

    #print(count)

        card_box1=page.locator(".d-flex.flex-column.col-12 > div:nth-child(1)")
        content=card_box1.inner_text().split('\n')
        df['company name']= ' '.join(content[0:])

        card_box1=page.locator(".d-flex.flex-column.col-12 > div:nth-child(2)")
        content=card_box1.inner_text().split('\n')
        df['location']= ' '.join(content[0:])

        card_box1=page.locator(".d-flex.flex-column.col-12 > div:nth-child(3)")
        content=card_box1.inner_text().split('\n')
        if 'Booth:' in content==True:
            df['Booth']= ' '.join(content[0:])

        for i in range(4,count+1,1):
            card_box1=page.locator(".d-flex.flex-column.col-12 > div:nth-child("+str(i)+")")
            content=card_box1.inner_text().split('\n')
            if 'Booth:' in content[0]==True:
                df['Booth']=content[0]
            else:
                df[content[0]]=' '.join(content[1:])
    
       
        if card_box.get_by_role('link', name= 'View more about this company').count()>0:
            supplier_url=card_box.get_by_role('link', name= 'View more about this company').get_attribute("href")
            df['supplier_url']=supplier_url
        else:
            df['supplier_url']='N/A'

        df['exhibitor_url']=page.url
    
    except:
        df={}

    with open('hktdc_'+prefix+'_L2.json', "a") as f:
        json_record = json.dumps(df)
        f.write(json_record + '\n')
        

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()

    j=0
    page = context.new_page()
    page.goto(domain+df2_L1['url'][0])
    scrape(page)

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
        print('Processing '+str(20*j+1)+' to '+str(20*j+20+1)+' out of '+str(len(df2_L1)))
        
        try:
            page1.goto(domain+df2_L1['url'][20*j+1], wait_until="domcontentloaded")
            scrape(page1)
        except:
            pass
        try:
            page2.goto(domain+df2_L1['url'][20*j+2], wait_until="domcontentloaded")
            scrape(page2)
        except:
            pass
        try:
            page3.goto(domain+df2_L1['url'][20*j+3], wait_until="domcontentloaded")
            scrape(page3)
        except:
            pass
        try:
            page4.goto(domain+df2_L1['url'][20*j+4], wait_until="domcontentloaded")
            scrape(page4)
        except:
            pass
        try:
            page5.goto(domain+df2_L1['url'][20*j+5], wait_until="domcontentloaded")
            scrape(page5)
        except:
            pass 
        try:
            page6.goto(domain+df2_L1['url'][20*j+6], wait_until="domcontentloaded")
            scrape(page6)
        except:
            pass
        try:
            page7.goto(domain+df2_L1['url'][20*j+7], wait_until="domcontentloaded")
            scrape(page7)
        except:
            pass
        try:
            page8.goto(domain+df2_L1['url'][20*j+8], wait_until="domcontentloaded")
            scrape(page8)
        except:
            pass       
        try:
            page9.goto(domain+df2_L1['url'][20*j+9], wait_until="domcontentloaded")
            scrape(page9)
        except:
            pass        
        try:
            page10.goto(domain+df2_L1['url'][20*j+10], wait_until="domcontentloaded")
            scrape(page10)
        except:
            pass        
        try:
            page11.goto(domain+df2_L1['url'][20*j+11], wait_until="domcontentloaded")
            scrape(page11)
        except:
            pass
        try:
            page12.goto(domain+df2_L1['url'][20*j+12], wait_until="domcontentloaded")
            scrape(page12)
        except:
            pass       
        try:
            page13.goto(domain+df2_L1['url'][20*j+13], wait_until="domcontentloaded")
            scrape(page13)
        except:
            pass        
        try:
            page14.goto(domain+df2_L1['url'][20*j+14], wait_until="domcontentloaded")
            scrape(page14)
        except:
            pass     
        try:
            page15.goto(domain+df2_L1['url'][20*j+15], wait_until="domcontentloaded")
            scrape(page15)
        except:
            pass     
        try:
            page16.goto(domain+df2_L1['url'][20*j+16], wait_until="domcontentloaded")
            scrape(page16)
        except:
            pass
        try:
            page17.goto(domain+df2_L1['url'][20*j+17], wait_until="domcontentloaded")
            scrape(page17)
        except:
            pass
        try:
            page18.goto(domain+df2_L1['url'][20*j+18], wait_until="domcontentloaded")
            scrape(page18)
        except:
            pass 
        try:
            page19.goto(domain+df2_L1['url'][20*j+19], wait_until="domcontentloaded")
            scrape(page19)
        except:
            pass   
        try:
            page20.goto(domain+df2_L1['url'][20*j+20], wait_until="domcontentloaded")
            scrape(page20)
        except:
            pass     


    r=len(df2_L1) %20
    
    if r==0:
        f=20
        l=int(len(df2_L1)/20)-1
    else:
        f=r
        l=int(len(df2_L1)/20)

    print('Processing '+str(20*l+1)+' to '+str(20*l+f)+' out of '+str(len(df2_L1)))
    for i in range(1,f,1):
        try:
            page1.goto(domain+df2_L1['url'][20*l+i])
            scrape(page1)
        except:
            pass
        #print(20*l+i)
        
    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
    df = pd.read_json('/Users/rowena/Other Projects/external_data_study/Result/Exhibition Organizers/HKTDC/'+prefix+'/hktdc_'+prefix+'_L2.json', orient='records', lines=True)

    df.to_csv('/Users/rowena/Other Projects/external_data_study/Result/Exhibition Organizers/HKTDC/'+prefix+'/hktdc_'+prefix+'_L2.csv',index=False)

