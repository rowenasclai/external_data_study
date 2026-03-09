
from playwright.sync_api import Playwright, sync_playwright, expect
import os
import pandas as pd

import asyncio

import numpy as np 
import re, json 
import time
import sqlite3
import io
from datetime import datetime

from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3.1")


url='https://www.epd.gov.hk/epd/english/news_events/notices/notices.html'

domain='https://www.epd.gov.hk/epd/english/news_events/notices/'

#prefix=input('What is the prefix of your exhibition?')
#os.chdir("/Users/rowena/Other Projects/external_data_study/Result/HKTDC/") 
#os.makedirs(prefix, exist_ok=True)
#os.chdir("/Users/rowena/Other Projects/external_data_study/Result/HKTDC/"+prefix) 

def get_date (row): 
    if row is not None: 
        x = row
        y = re.search (date_pattern,x, re.IGNORECASE)
        if y is not None:
            return y.group().strip()
        else:
            return ''

def get_sum (row): 
    if row is not None: 
        y = re.search (date_pattern,row, re.IGNORECASE)
        if y is not None:
            return row.replace(y.group(),'').strip()
        else:
            return ''

def get_awardee (row): 
    prompt = "Valid examples of company name include: \nAECOM Asia Company Limited\nATAL Engineering Limited\nBased on the example provided and other common company name format, try to extract company name from following. No need to show any explanation. :\n"
    return llm.invoke(prompt + str(row))

def process_export(url,dpt,suffix):
    from datetime import datetime

    batch_time = datetime.now() 
    
    df2 = pd.read_csv(suffix+'.csv')
    
    df2['batch_time'] = batch_time
    df2['department'] = dpt
    
    df2=df2.replace('\n',' ', regex=True)
    df3 = pd.DataFrame()

    if 'Contract Number' in df2.columns:
        df3[['ref']]=df2[['Contract Number']]
    elif 'Tender Reference' in df2.columns:
        df2=df2[df2['Tender Reference']!='Tender Reference']
        df2=df2[df2['Tender Reference']!='']
        df3[['ref']]=df2[['Tender Reference']]
    elif 'Agreement No. (1)' in df2.columns:
        df3[['ref']]=df2[['Agreement No. (1)']]
    elif 'Agreement Number' in df2.columns:
        df3[['ref']]=df2[['Agreement Number']]
    elif 'CONTRACT/TENDER REF.' in df2.columns:
        df3[['ref']]=df2[['CONTRACT/TENDER REF.']]
    elif 'Contract No.' in df2.columns:
        df3[['ref']]=df2[['Contract No.']]
    elif 'Agreement No. and Title' in df2.columns:
        df3[['ref']]=df2[['Agreement No. and Title']] 

    if 'start' in df2.columns:
        df3[['start']]=df2[['start']]

    if 'end' in df2.columns:
        df3[['end']]=df2[['end']]
        
    df3['department'] = df2['department']
    df3[['url']]=df2[['url']]
    df3['batch_time']=df2['batch_time']

    if 'Description' in df2.columns:
        df3[['description']]=df2[['Description']]
    elif 'Contract Title' in df2.columns and 'Nature of Works' in df2.columns:
        df3['description']=df2['Contract Title']+ ' / ' + df2['Nature of Works']
    elif 'Contract Title' in df2.columns:
        df3['description']=df2['Contract Title']
    elif 'Agreement Title' in df2.columns:
        df3['description']=df2['Agreement Title']
    elif 'TITLE' in df2.columns:
        df3['description']=df2['TITLE']
    elif 'Subject' in df2.columns:
        df3[['description']]=df2[['Subject']]

    if 'award_date' in df2.columns:
        df3[['award_date']]=df2[['award_date']]
    elif 'Date of award' in df2.columns:
        df3[['award_date']]=df2[['Date of award']]
    
    if 'Date of Award' in df2.columns and 'award_date' not in df2.columns:
        df3['award_date']=df2['Date of Award']
        
    if 'Contractor(s) and Address(es)' in df2.columns:
        df3['awardee']=df2['Contractor(s) and Address(es)'].map(get_awardee)
    elif 'Contractor(s) & Address(es)' in df2.columns:
        df3['awardee']=df2['Contractor(s) & Address(es)'].map(get_awardee)
    elif 'Contractor(s)' in df2.columns:
        df3['awardee']=df2['Contractor(s)']
    elif 'Contractor' in df2.columns:
        df3['awardee']=df2['Contractor']
    elif 'Name of Successful Consultant' in df2.columns:
        df3['awardee']=df2['Name of Successful Consultant']
    elif 'Contractor Name' in df2.columns:
        df3['awardee']=df2['Contractor Name']
    elif 'Name of Successful Consultant(s)' in df2.columns:
        df3['awardee']=df2['Name of Successful Consultant(s)']
    elif 'Name of Contractor' in df2.columns:
        df3['awardee']=df2['Name of Contractor']
    elif 'awardee' in df2.columns:
        df3['awardee']=df2['awardee']


    if 'Estimated Awarded Sum / Contract Award Date' in df2.columns:
        df3['sum']=df2['Estimated Awarded Sum / Contract Award Date'].map(get_sum)
        df3['award_date']=df2['Estimated Awarded Sum / Contract Award Date'].map(get_date) 
    elif 'Amount / Contract Award Date' in df2.columns:
        df3['sum']=df2['Amount / Contract Award Date'].map(get_sum)
        df3['award_date']=df2['Amount / Contract Award Date'].map(get_date) 
    elif 'Contract Sum' in df2.columns:
        df3['sum']=df2['Contract Sum']
    elif 'Consultancy Cost (2)' in df2.columns:
        df3['sum']=df2['Consultancy Cost (2)']
    elif 'Contract Sum ($M)' in df2.columns:
        df3['sum']=df2['Contract Sum ($M)']
    elif 'Contract Sum* (HK$ M)' in df2.columns:
        df3['sum']=df2['Contract Sum* (HK$ M)']   
    elif 'Awarded Sum (million)' in df2.columns:
        df3['sum']=df2['Awarded Sum (million)']
    elif 'Fee' in df2.columns:
        df3['sum']=df2['Fee']
    elif 'Contract Value ($M)' in df2.columns:
        df3['sum']=df2['Contract Value ($M)']
    elif 'sum' in df2.columns:
        df3['sum']=df2['sum']     
    elif 'Original Contract Sum' in df2.columns:
        if df2['Original Contract Sum'] is not None:
            df3['sum']=df2['Original Contract Sum']
    elif 'Contract Value' in df2.columns:
        if df2['Contract Value'] is not None:
            df3['sum']=df2['Contract Value']

    if 'Awarded Quantity' in df2.columns:
        df3['period'] =df2['Awarded Quantity']
    elif 'Date of Commencement' in df2.columns and 'Anticipated Date of Completion' in df2.columns:
        df3['start']=df2['Date of Commencement']
        df3['end']=df2['Anticipated Date of Completion']
    elif 'Date of Commencement' in df2.columns and 'Original Completion Date' in df2.columns:
        df3['start']=df2['Date of Commencement']
        df3['end']=df2['Original Completion Date']
    elif 'Contract Period' in df2.columns:
        df3['period']=df2['Contract Period']

    df3[pd.isna(df3['ref'])==False]

    df3.to_csv(suffix+'_out.csv', index=False)  

def combine():
    df = pd.DataFrame()
    df = df._append(pd.read_csv('epd_out.csv'))
    df = df._append(pd.read_csv('dsd_out.csv'))
    df = df._append(pd.read_csv('cesd_out.csv'))
    df = df._append(pd.read_csv('cesd_consultant_out.csv'))
    df = df._append(pd.read_csv('emsd_out.csv'))
    df = df._append(pd.read_csv('emsd2_consultant_out.csv'))
    df = df._append(pd.read_csv('hyd_out.csv'))
    df = df._append(pd.read_csv('hyd_consultant_out.csv'))
    df = df._append(pd.read_csv('wsd_out.csv'))
    df = df._append(pd.read_csv('wsd2_consultant_out.csv'))
    df = df._append(pd.read_csv('td_out.csv'))
    df = df._append(pd.read_csv('td2_consultant_out.csv'))
    df = df._append(pd.read_csv('hkaa_out.csv'))
    df = df._append(pd.read_csv('gld_out.csv'))
    df = df._append(pd.read_csv('hahk_out.csv'))
    #df.to_json('/Users/rowena/data/combined.json', orient = 'records', compression = 'infer', index = 'false')
    df.to_csv('/Users/rowena/data/combined.csv', index=False, encoding='utf-8')  

def run(playwright: Playwright, url, domain, suffix) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded")

    page1 = context.new_page()
    #page2 = context.new_page()

    if suffix=='esd':
        cl=".node__content"
        list1=page.locator(f"{cl}")
        list2=list1.locator('ul > li')
    
    elif suffix=='dsd':
        cl='#resultTable'
        list1=page.locator(f"{cl}")
        all_links=list1.get_by_role('link')

    elif suffix=='cedd':
        cl='.colorTable.tenderTbl'
        list1=page.locator(f"{cl}")
        all_links=list1.get_by_role('link')
        all_date=list1.locator('tbody').locator('tr')
        all_date_list=[]
        
        for k in range(all_date.count()):
            all_date_list.append(all_date.nth(k).locator('td').nth(2).inner_text())

    elif suffix=='cedd_consultant':
        cl='.colorTable.tenderTbl'
        list1=page.locator(f"{cl}")
        header=page.locator("thead").locator("th")
        header_list=[]
        df=pd.DataFrame()

        cnt=list1.locator("tbody").locator("tr")
        
        for k in range(header.count()):
            header_list.append(header.nth(k).inner_text())
            
            for j in range(cnt.count()):
                df.loc[j,f"{header.nth(k).inner_text()}"]=cnt.nth(j).locator("td").nth(k).inner_text()

        df['award_date']=pd.to_datetime(df['Award Date'], format='%d/%m/%Y')
        df['start']=pd.to_datetime(df['Commencement Date'], format='%d/%m/%Y')
        df['end']=pd.to_datetime(df['Estimated Completion Date'], format='%d/%m/%Y')

        df['url']=url
        #df.columns=header_list
 
        #print(cnt.nth(0).inner_text())

    
    elif suffix=='emsd':
        cl='.color_table'
        list1=page.locator(f"{cl}")
        df=pd.DataFrame()
        
        for j in range(list1.count()):
            col=list1.nth(j).locator('.v_th')
            value=list1.nth(j).locator('td')
            
            for k in range(col.count()):
                df.loc[j,f"{col.nth(k).inner_text()}"]=value.nth(k).inner_text()
            df.loc[j,'url']=domain+value.nth(0).get_by_role('link',name=f"{value.nth(0).inner_text()}").get_attribute("href")

    elif suffix=='emsd_consultant':
        cl='.tab_list'
        list1=page.locator(f"{cl}")
        df=pd.DataFrame()
        
        for j in range(list1.count()):
            col=list1.nth(j).locator('.th')
            value=list1.nth(j).locator('td')

            for k in range(col.count()):
                df.loc[j,f"{col.nth(k).inner_text()}"]=value.nth(k).inner_text()
            df.loc[j,'url']=domain+value.nth(0).get_by_role('link',name=f"{value.nth(0).inner_text()}").get_attribute("href")
        
        df['url']=url
    elif suffix=='hkaa':
        cl='.contentContainer.listingTable'
        list1=page.locator(f"{cl}")
        df=pd.DataFrame()

        list_contract=list1.locator(".resultDataContainerBox")

        for k in range(list_contract.locator(".typeData").count()):
            df.loc[k,'TYPE']=list_contract.locator(".typeData").nth(k).inner_text()
            df.loc[k,'CONTRACT/TENDER REF.']=list_contract.locator(".contractData").nth(k).text_content()
            df.loc[k,'TITLE']=list_contract.locator(".titleData").nth(k).inner_text().strip().replace('\n',' ')
            df.loc[k,'TITLE']=re.sub(r'\s+', ' ', df.loc[k,'TITLE'])

            if list_contract.get_by_role('link',name=df.loc[k,'TITLE']).count()>0:
                df.loc[k,'url']=domain+list_contract.get_by_role('link',name=df.loc[k,'TITLE']).get_attribute("href")
                #print(df.loc[k,'url'])
                page1.goto(df.loc[k,'url'])
                content=page1.locator(".contentContainer.tenderDetail.idol-index.html-content")
                #print(content.inner_text())
                df.loc[k,'detail description']=content.inner_text()
                
                df.loc[k,'awardee'] = get_awardee(content.inner_text()) 
                
                if re.search (r'HK\$[\d,.]+( )?(million)?' ,content.inner_text()) is not None:
                    df.loc[k,'sum'] =  re.search (r'HK\$[\d,.]+( )?(million)?' ,content.inner_text())[0]
                #df.loc[k,'sum'] =  re.search (r'HK\$[\d,.]+( )?(million)?' ,content)
                
            df.loc[k,'PUBLISH']=list_contract.locator(".closingDateData").nth(k).inner_text()
            df.loc[k,'award_date']=datetime.strptime(df.loc[k,'PUBLISH'], '%Y-%m-%d').date().strftime('%d %B %Y')
        
    elif suffix in ('hyd','hyd_consultant'):
        cl='#content'
        list1=page.locator(f"{cl}")
        header=page.locator("thead").locator("th")
        header_list=[]
        df=pd.DataFrame()

        cnt=list1.locator("tbody").locator("tr")
        
        for k in range(header.count()):
            header_list.append(header.nth(k).inner_text().replace('\n',' '))
            
            for j in range(cnt.count()):
                df.loc[j,f"{header_list[k]}"]=cnt.nth(j).locator("td").nth(k).inner_text()
                #df.loc[j,'award_date']=datetime.strptime(df.loc[j,'Award Date (dd/mm/yyyy)'], '%d/%m/%Y').date().strftime('%d %B %Y')

        #print(header_list)

        df['award_date']=pd.to_datetime(df['Award Date (dd/mm/yyyy)'], format='%d/%m/%Y')

        df['url']=url

    elif suffix in ('wsd'):
        cl='#divList'
        list1=page.locator(f"{cl}")
        header=page.locator("thead").locator("th")
        header_list=[]
        df=pd.DataFrame()

        cnt=list1.locator("tbody").locator("tr")
        
        for k in range(header.count()):
            header_list.append(header.nth(k).inner_text().replace('\n',' '))
            
            for j in range(cnt.count()):
                df.loc[j,f"{header_list[k]}"]=cnt.nth(j).locator("td").nth(k).inner_text()
                #df.loc[j,'award_date']=datetime.strptime(df.loc[j,'Award Date (dd/mm/yyyy)'], '%d/%m/%Y').date().strftime('%d %B %Y')
        for j in range(cnt.count()):
            if cnt.get_by_role('link',name=df.loc[j,'Contract Title']).count()>0:
                df.loc[j,'url']=domain+cnt.get_by_role('link',name=df.loc[j,'Contract Title']).nth(0).get_attribute("href")

        #print(header_list)

        df['award_date']=pd.to_datetime(df['Awarded Date'], format='%d/%m/%Y')

        #df['url']=url
    elif suffix in ('wsd_consultant'):
        cl='.style_table'
        list1=page.locator(f"{cl}").nth(0)
        header=page.locator(f"{cl}").nth(0).locator("tbody").locator("tr").nth(0)

        #print(header.inner_text())
        header_list=[]
        df=pd.DataFrame()

        cnt=page.locator(f"{cl}").nth(0).locator("tbody").locator("tr")
        #print(cnt.nth(1).locator("td").nth(0).inner_text())
        
        for k in range(header.locator("th").count()):
            header_list.append(header.locator("th").nth(k).inner_text().replace('\n',' '))
            
            for j in range(1,cnt.count()):
                df.loc[j,f"{header_list[k]}"]=cnt.nth(j).locator("td").nth(k).inner_text()
                #df.loc[j,'award_date']=datetime.strptime(df.loc[j,'Award Date (dd/mm/yyyy)'], '%d/%m/%Y').date().strftime('%d %B %Y')

        #print(header_list)

        df['start']=pd.to_datetime(df['Commencement Date'], format='%d/%m/%Y')
        df['end']=pd.to_datetime(df['Estimated Completion Date'], format='%d/%m/%Y')
        df['url']=url

    elif suffix in ('td','td_consultant'):
        cl='.content_table1'
        list1=page.locator(f"{cl}")
        header=page.locator("tbody").locator("th")
        header_list=[]
        df=pd.DataFrame()

        cnt=list1.locator("tbody").locator("tr")
        
        for k in range(header.count()):
            header_list.append(header.nth(k).inner_text().replace('\n',' '))
            
            for j in range(1,cnt.count()):
                #print(cnt.nth(j).locator("td").count())
                #print(cnt.nth(j).inner_text())    
                if cnt.nth(j).locator("td").count()==5:
                    df.loc[j,f"{header_list[k]}"]=cnt.nth(j).locator("td").nth(k).inner_text()  
                
        df['url']=url
        #df['award_date']=df['Date of Award'].replace(,'')

        #print(df['award_date'])
        #print(df)

        #print(header_list)
        # if df['Date of Award']:
        #     df['award_date']=pd.to_datetime(df['Date of Award'], format='%d.%m.%Y')

        #print(df)
    elif suffix in ('gld'):
        tbl=page.get_by_role("table", name="Table #1 - The following")
        #print(tbl.inner_text())
        
        cl='span.deptName'
        page.wait_for_selector("span.deptName")
        list1=page.locator(f"{cl}")

        all_th=tbl.locator('tr > th')
        all_td=tbl.locator('tr > td')
        all_tr=tbl.locator('tr')

        all_tr_list=all_tr.all_inner_texts()
        dept_name=page.locator('span.deptName')

        #print(all_tr_list[0])
        dpt1=''
        df=pd.DataFrame()
        tmp=pd.DataFrame()

        #print(all_tr_list[3])
        #print(all_tr_list[3].split('\n'))
        #print(all_tr.nth(13).locator('td').all_inner_texts())
        print(all_tr.nth(13).locator('td').nth(0).all_inner_texts())

        for i in range(len(all_tr_list)):
            if len(all_tr_list[i].split('\n'))>1 and all_tr_list[i].split('\n')[1] in dept_name.all_inner_texts():
                dpt1=all_tr_list[i].split('\n')[1]
                tmp=pd.DataFrame()
                #print(all_tr_list[i])
            elif 'Tender Reference' in all_tr_list[i]:
                th=all_tr_list[i].split('\n')
                tmp=pd.DataFrame()
                #print('item 2'+all_tr_list[i])
            else: 
                if all_tr.nth(i).locator('td').count() == 3:
                    tmp.loc[i,'Contractor(s) & Address(es)']=all_tr.nth(i).locator('td').nth(0).inner_text()
                    tmp.loc[i,'Item/Quantity']=all_tr.nth(i).locator('td').nth(1).inner_text()
                    tmp.loc[i,'Amount / Contract Award Date']=all_tr.nth(i).locator('td').nth(2).inner_text()
                elif all_tr.nth(i).locator('td').count() == 6:
                    tmp.loc[i,'Tender Reference']=all_tr.nth(i).locator('td').nth(0).inner_text()
                    tmp.loc[i,'Tendering Procedure	']=all_tr.nth(i).locator('td').nth(1).inner_text()
                    tmp.loc[i,'Particulars']=all_tr.nth(i).locator('td').nth(2).inner_text()
                    tmp.loc[i,'Contractor(s) & Address(es)']=all_tr.nth(i).locator('td').nth(3).inner_text()
                    tmp.loc[i,'Item/Quantity']=all_tr.nth(i).locator('td').nth(4).inner_text()
                    tmp.loc[i,'Amount / Contract Award Date']=all_tr.nth(i).locator('td').nth(5).inner_text()     
                tmp['department']=dpt1

            tmp=tmp.replace('\n',' ')
            df=df.replace('\n',' ')
            df=pd.concat([df,tmp],axis=0)
            
    elif suffix in ('hahk'):
        page.wait_for_load_state('networkidle') 
        #page.get_by_role('link',name="CONTRACT AWARD NOTICE").click()
        referral_link=page.locator("iframe[name=\"childframe\"]").content_frame.get_by_role("link", name="CONTRACT AWARD NOTICE").get_attribute("href")
        #print(domain+referral_link)
        page1.goto(domain+referral_link)
        all_tr=page1.locator('tr')
        
        all_tr_list=all_tr.all_inner_texts()
        df=pd.DataFrame()
        month=''

        #print(all_tr.all_inner_texts())
        for i in range(len(all_tr_list)):     
            tmp=pd.DataFrame()
            #print(all_tr.nth(i).locator('td').count())
            if 'Awarded Month:' in all_tr_list[i]:
                month=all_tr_list[i]
            elif all_tr.nth(i).locator('td').count()==11:
                #tmp=pd.DataFrame(all_tr_list[i].split('\n')).transpose()
                tmp.loc[i,'Hospital']=all_tr.nth(i).locator('td').nth(0).inner_text()
                tmp.loc[i,'Tender Reference']=all_tr.nth(i).locator('td').nth(1).inner_text()
                tmp.loc[i,'Subject']=all_tr.nth(i).locator('td').nth(2).inner_text()
                tmp.loc[i,'Tendering Procedure']=all_tr.nth(i).locator('td').nth(3).inner_text()
                tmp.loc[i,'Contractor(s) & Address(es)']=all_tr.nth(i).locator('td').nth(4).inner_text()
                tmp.loc[i,'Item']=all_tr.nth(i).locator('td').nth(5).inner_text()
                tmp.loc[i,'Contract Period']=all_tr.nth(i).locator('td').nth(6).inner_text()
                tmp.loc[i,'Estimated Contract Amount']=all_tr.nth(i).locator('td').nth(7).inner_text()
                tmp.loc[i,'Date of Award']=all_tr.nth(i).locator('td').nth(8).inner_text()
                # tmp.columns=['Hospital','Tender Reference',	'Subject',	'Tendering Procedure',	'Contractor(s) & Address(es)',	'Item',	'Contract Period',	'Estimated Contract Amount',	'Date of Award']
                tmp.loc[i,'month']=month.replace('Awarded Month: ','').replace('\t',' ').strip()
                # 
                #print(tmp)
            df=pd.concat([df,tmp],axis=0)
            df['url']=page1.url
    #print(df)
    
    if suffix=='esd':
        cl1='.p-table'
    elif suffix=='dsd':
        cl1='.col-lg-9.content'
    elif suffix=='cedd':
        cl1='#content'
    elif suffix=='emsd':
        cl1=".color_table"
        
    if suffix not in ('emsd','cedd_consultant','emsd_consultant','hkaa','hyd','hyd_consultant','wsd','wsd_consultant','td','td_consultant',
                    'gld','hahk'):
        df=pd.DataFrame()
        for i in range(all_links.count()):
        
            link=all_links.nth(i).get_attribute("href")
            link_go=domain+link
            page1.goto(link_go)

            if suffix=='esd':

                tbl=page1.locator(f"{cl1}")
                header=tbl.locator("thead")
                t_col=header.locator('th')
        
            #print(header.nth(j).inner_text())
        
                row=tbl.locator('tr')
                df=pd.DataFrame()
                t=[None]*t_col.count()

        
                for j in range(row.count()):
                    col=row.nth(j).locator('td')

                    for k in range(col.count()):
                #print('col '+str(k)+col.nth(k).inner_text())
                        df.loc[j,k]=col.nth(k).inner_text()
                
                for k in range(t_col.count()):
            #df_h.loc[0,k]=t_col.nth(k).inner_text()
                    t[k]=t_col.nth(k).inner_text()

                df.columns=t
                df['url']=link_go

            elif suffix=='dsd':
                tbl=page1.locator(f"{cl1}")
                cntract=tbl.locator(".col-md-12.contract_no")
                df.loc[i,'Tender Reference']=cntract.inner_text()
                desc=tbl.locator("h2")
                df.loc[i,'Subject']=desc.inner_text()
                df['url']=link_go

                content=tbl.locator(".content").locator(".row")
                for k in range(content.count()):
                    col_name=content.nth(k).locator("div").nth(0)
                    col_content=content.nth(k).locator("div").nth(1)
                    df.loc[i,f"{col_name.inner_text()}"]=col_content.inner_text()
                
            elif suffix=='cedd': 
                tbl=page1.locator(f"{cl1}")
                header=page1.locator("h3").all()
                all_text=tbl.inner_text().split('\n')
                header_list=[]

                df.loc[i,'url']=link_go
                df.loc[i,'award_date']=all_date_list[i]

                for head in header:
                    header_list.append(head.inner_text())


                for k in range(1,len(all_text)):
                    if all_text[k-1][-1:]==":" and all_text[k-1] in header_list:
                        col_name=all_text[k-1][:-1].strip()
                        text=''
                        text=text+' '+all_text[k]
                        text=text.strip()
                        df.loc[i,col_name]=text
                    elif (all_text[k-1][-1:]!=":" or all_text[k-1] not in header_list) and (all_text[k][-1:]!=":" or all_text[k] not in header_list):
                        text=text+' '+all_text[k]
                        text=text.strip()
                        df.loc[i,col_name]=text
                df['award_date']=pd.to_datetime(df['award_date'], format='%d/%m/%Y')

    #print(df)
  
    df.to_csv(suffix+'.csv', mode='a', index=False, header=True)

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    url='https://www.epd.gov.hk/epd/english/news_events/notices/notices.html'
    domain='https://www.epd.gov.hk/epd/english/news_events/notices/'
    suffix='epd'
    dpt='Environmental Protection Department'
    date_pattern = r"\d{1,2} (january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)( |\xa0)\d{2,4}"
    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url = 'https://www.dsd.gov.hk/EN/Our_Projects/Contracts_Consultancies_Awarded/index.html'
    domain='https://www.dsd.gov.hk/EN/Our_Projects/Contracts_Consultancies_Awarded/'
    suffix='dsd'
    dpt='Drainage Services Department'
    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url = 'https://www.cedd.gov.hk/eng/tender-notices/contracts/contracts-awarded/index.html'
    domain='https://www.cedd.gov.hk/'
    suffix='cedd'
    dpt = 'Civil Engineering and Development Department'
    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url='https://www.cedd.gov.hk/eng/tender-notices/consultancy-agreements/consultancies-awarded/index.html'
    domain='https://www.cedd.gov.hk/'
    suffix='cedd_consultant'
    dpt = 'Civil Engineering and Development Department'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url = 'https://www.emsd.gov.hk/en/tenders_contracts_and_consultancies/tender_notices/award_of_tender/index.html'
    domain='https://www.emsd.gov.hk'
    suffix='emsd'
    dpt='Electrical and Mechanical Services Department'
    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url = 'https://www.emsd.gov.hk/en/tenders_contracts_and_consultancies/tender_notices/award_of_consultancies/index.html'
    domain='https://www.emsd.gov.hk'
    suffix='emsd_consultant'
    dpt='Electrical and Mechanical Services Department'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url='https://www.hongkongairport.com/en/airport-authority/tender-notices/notice-of-contract-award.page'
    domain='https://www.hongkongairport.com'
    suffix='hkaa'
    dpt='Hong Kong Airport Authority'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)
    url='https://www.hyd.gov.hk/en/tender_notices/contracts/awarded/index.html'
    domain='https://www.hyd.gov.hk/'
    suffix='hyd'
    dpt='Highways Department'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url='https://www.hyd.gov.hk/en/tender_notices/contracts/awarded/index.html'
    domain='https://www.hyd.gov.hk/'
    suffix='hyd_consultant'
    dpt='Highways Department'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url='https://www.wsd.gov.hk/en/tenders-contracts-and-consultancies/contracts/active-wsd-capital-works-contracts/index.html'
    domain='https://www.wsd.gov.hk/'
    suffix='wsd'
    dpt='Water Supplies Department'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url='https://www.wsd.gov.hk/en/tenders-contracts-and-consultancies/consultancies/award-consultancies/index.html'
    domain='https://www.wsd.gov.hk/'
    suffix='wsd_consultant'
    dpt='Water Supplies Department'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url='https://www.td.gov.hk/en/tender_notices/award_of_contracts_and_consultancies/works_contract/index.html'
    domain='https://www.wsd.gov.hk/'
    suffix='td'
    dpt='Transport Department'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)
    url = 'https://www.td.gov.hk/en/tender_notices/award_of_contracts_and_consultancies/non_works_contract/index.html'
    domain='https://www.wsd.gov.hk/'
    suffix='td_consultant'
    dpt='Transport Department'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)
    url ='https://pcms2.gld.gov.hk/iprod/#/scn00101'
    domain='https://pcms2.gld.gov.hk/'
    suffix='gld'
    dpt='gld'

    #run(playwright,url,domain,suffix)
    #process_export(url,dpt,suffix)

    url='https://www.ha.org.hk/visitor/ha_visitor_index.asp?Content_ID=2001&Lang=ENG&Dimension=10'
    domain='https://www.ha.org.hk/visitor/'
    suffix='hahk'
    dpt='hahk'

    #run(playwright,url,domain,suffix)
    process_export(url,dpt,suffix)
    #combine()
    

