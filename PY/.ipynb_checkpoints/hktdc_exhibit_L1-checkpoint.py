import re
from playwright.sync_api import Playwright, sync_playwright, expect
import os

import asyncio
import json
import pandas as pd

#page.locator("div").filter(has_text=re.compile(r"^Shown 11-20 of Total Result 1820$"))

#url='https://www.hktdc.com/event/hkjewellery/en/exhibitor-list?pageNum=1&pageSize=50'
domain='https://www.hktdc.com'

prefix=input('What is the prefix of your exhibition?')
os.chdir("/Users/rowena/Other Projects/external_data_study/Result/HKTDC/") 
os.makedirs(prefix, exist_ok=True)
os.chdir("/Users/rowena/Other Projects/external_data_study/Result/HKTDC/"+prefix) 

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    #l=page.locator("div").filter(has_text=re.compile(r"^Total Result$"))
    #print(l.inner_text())
    url='https://www.hktdc.com/event/'+prefix+'/en/exhibitor-list?pageNum=1&pageSize=50'
    page.goto(url)
    check_figure=page.locator("div").filter(has_text=re.compile(r"^Shown.*Total Result"))
    final_figure_text=check_figure.text_content()
    result_l=final_figure_text.find('Total Result')
    l_div=int(final_figure_text[result_l+13:])

    print('Processing '+str(1)+' - '+str(50)+' out of '+str(l_div))

    for j in range(1,int(l_div/50)+2,1):
        url='https://www.hktdc.com/event/'+prefix+'/en/exhibitor-list?pageNum='+str(j)+'&pageSize=50'
        print('Processing '+str((j-1)*50+1)+' - '+str((j-1)*50+49)+' out of '+str(l_div))
        page.goto(url)
        data={}
    #test=page.locator(".d-flex.flex-column.vep-p-4")
    #check=page.locator(".d-flex.flex-column.vep-p-4.div").filter(has_text=True).first
    #link=check.get_by_role("link", name=check).get_attribute("href")
    #check1=page.locator("div").filter(has_text=True).nth(1)
    #check1=page.locator("div:nth-child(1) > .d-flex.flex-column.vep-p-4")
        try:
            check1=page.locator(".d-flex.flex-column.vep-p-4").first
            my_list=check1.inner_text().split('\n')
            data['Company Name']=check1.inner_text().split('\n')[0]
            data['Location']=check1.inner_text().split('\n')[1]
            pattern = r'^Booth.*'  # Matches items ending with "berry"
            # Create a new list containing only the items that match the pattern
            matching_items = [item for item in my_list if re.search(pattern, item)]
            data['Booth']=matching_items
            data['url']=check1.get_by_role('link', name= check1.inner_text().split('\n')[0]).get_attribute("href")

            with open('hktdc_'+prefix+'_L1.json', "a") as f:
                json_record = json.dumps(data)
                f.write(json_record + '\n')
        except:
            pass
    #print(check1.inner_text())
    #print(data)

        for i in range(2,51,1):  
            if (j-1)*50+i-1<l_div:
                #print('Processing '+str((j-1)*50+1)+' - '+str((j-1)*50+49)+' out of '+str(l_div))
                check=page.locator("div:nth-child("+str(i)+") > .d-flex.flex-column.vep-p-4")
        #print(check.inner_text())
                data['Company Name']=check.inner_text().split('\n')[0]
                data['Location']=check.inner_text().split('\n')[1]
                pattern = r'^Booth.*'  # Matches items ending with "berry"
            # Create a new list containing only the items that match the pattern
                matching_items = [item for item in my_list if re.search(pattern, item)]
                data['Booth']=matching_items
                
                try:
                    data['url']=check.get_by_role('link', name= data['Company Name']).get_attribute("href")
                except:
                    pass
                
                with open('hktdc_'+prefix+'_L1.json', "a") as f:
                    json_record = json.dumps(data)
                    f.write(json_record + '\n')
            else:
                pass
        #print(data)
    
    #print(check1.inner_text())
    #print(link)

    
    #page.locator("div:nth-child(2) > .d-flex.flex-column.vep-p-4")
    #all_links=test.get_by_role('link').get_attribute("href")

    # card_box=page.get_by_text("Company DetailsNature of")
    # all_text=card_box.inner_text()
    # data[all_text.split('\n')[1]]=all_text.split('\n')[2]
    #card_box=page.locator(".d-flex.flex-column.col-12")

    #print(all_links)

    #print(data)

    #print(name_el.inner_text().split('\n')[3])
    #data['company_name'] = name_el

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
    
    df = pd.read_json('/Users/rowena/Other Projects/external_data_study/Result/HKTDC/'+prefix+'/hktdc_'+prefix+'_L1.json', orient='records', lines=True)

    df.to_csv('/Users/rowena/Other Projects/external_data_study/Result/HKTDC/'+prefix+'/hktdc_'+prefix+'_L1.csv',index=False)