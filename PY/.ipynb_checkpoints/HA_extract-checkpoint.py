#!/usr/bin/env python
# coding: utf-8

# In[1085]:


import pdfplumber
import pandas as pd
import requests
import io
import re
import os

import camelot.io as camelot
from pathlib import Path


# In[1098]:


from datetime import datetime
from dateutil.relativedelta import relativedelta

current_datetime = datetime.now()
past_1_month = current_datetime  - relativedelta(months=1)
past_2_month = current_datetime  - relativedelta(months=2)
past_3_month = current_datetime  - relativedelta(months=3)

# Format as "YYYY-MM-DD HH:MM:SS"
formatted_string = current_datetime.strftime("%b_%Y")
formatted_string_P1 = past_1_month.strftime("%b_%Y")
formatted_string_P2 = past_2_month.strftime("%b_%Y")
formatted_string_P3 = past_3_month.strftime("%b_%Y")


# In[1111]:


# for string in [formatted_string,formatted_string_P1,formatted_string_P2,formatted_string_P3]:
#     pdf_url="https://www.housingauthority.gov.hk/en/common/pdf/business-partnerships/tenders/BP_Tender_Award_"+string+".pdf"

#     try:
#         response = requests.get(pdf_url)
#         response.raise_for_status()
#         pdf_path = "BP_Tender_Award_"+string+".pdf"

#         path_obj = Path(pdf_path)

#         if not path_obj.exists():
#             with open(pdf_path, "wb") as f:
#                 f.write(response.content)
#             #path_obj.write_text(content)
#         else:
#             print(f"The file '{pdf_path}' already exists. Not writing to it.")

#     except Exception as e:
#         print(f"No File exists: {pdf_url}")




# In[925]:


def get_dynamic_v_lines(page):
    words = page.extract_words()
    width = int(page.width)

    l_header=['PROCEDURE']
    r_header=['PROCEDURE',#'ADDRESS(ES)',
              'DATE']

    gaps = []

    for w in words:
        text = w['text'].upper()
        upper=w['x0']
        lower=w['x1']+21
        if text in l_header:
            #print(text+':'+str(upper))
            gaps.append(upper)
        if text =='ADDRESS(ES)':
            gaps.append(lower+35)
        elif text in r_header:
            #print(text+':'+str(lower+21))
            gaps.append(lower+16)
              
    # Create a 'hit map' of horizontal occupancy
    # occupancy = [0] * width
    # for w in words:
    #     for x in range(int(w['x0']), int(w['x1'])):
    #         if 0 <= x < width:
    #             occupancy[x] += 1

    
    # # Find the centers of the gaps (where occupancy is 0)
    # gaps = []
    # in_gap = False
    # start = 0
    # for x, count in enumerate(occupancy):
    #     if count <= 1 and not in_gap:
    #         start = x
    #         in_gap = True
    #     elif count > 1 and in_gap:
    #         gaps.append((start + x) // 2) # Midpoint of the white space
    #         in_gap = False
            
    # Filter to keep only the widest 4-5 gaps to avoid splitting words
    # Or simply return the edges + the gaps that fall near your expected columns
    return sorted(list(set([10, 810] + gaps)))


# In[1068]:


def get_dynamic_h_lines(page):
    h_lines = [10] # Start with your top margin
    words = page.extract_words()
    height = int(page.height)
    occupancy = [0] * height
    
    # 1. Find the header row (usually contains 'Contract' or 'Tender')
    # 2. Find the Division row (contains 'DIVISION')
    for w in words:
        text = w['text'].upper()
        
        # If we find a Division, we want a line right above it and right below it
        if "DIVISION" in text:
            h_lines.append(w['top'])
            if w['bottom']-max(h_lines)>=10:
                h_lines.append(w['bottom']+4)
            #print("DIVISION TOP "+str(w['top']))
            #print("DIVISION BOTTOM "+str(w['bottom']+4))
        elif "ADDRESS(ES)" in text :
            if w['top']-max(h_lines)>=10:
                h_lines.append(w['bottom'])
                h_lines.append(w['top'] -40)
                anchor=w['x0']
            h_lines.append(w['bottom'] )
        
        header_bottom=max(h_lines)

    for w in words:
        # Only track text below the header to avoid noise
        if w['bottom'] - header_bottom>=20:
            if w['top']-max(h_lines)>=50 and anchor-50<=w['x0']>=anchor+100:
                top=w['top']
                bottom=w['bottom']                      
                if w['bottom']>bottom-50:
                    #print(w['bottom'])
                    bottom=w['bottom']
                    h_lines.append(w['bottom']-20)
 
        
    return sorted(list(set(h_lines)))


# In[1136]:





# In[1352]:


def pdf_process(pdf_file, export_file):
#import pdfplumber
    pdf = pdfplumber.open(pdf_file) # See note below

    tmp=pd.DataFrame()

    for i in range(len(pdf.pages)):
        page = pdf.pages[i]

        df_h=get_dynamic_h_lines(page)
        df_v=get_dynamic_v_lines(page)

        settings={
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines", 
            "explicit_vertical_lines": df_v,#df_v,
            "explicit_horizontal_lines":  df_h,#df_h_test,
            "snap_tolerance": 3,
            "join_tolerance": 3
        }

        table = page.extract_table(table_settings=settings)
        tmp1=pd.DataFrame(table)
        #tmp.columns=tmp.columns.replace('\n',' ', regex=True)
        tmp1.columns=tmp1.iloc[min(tmp1[tmp1[0]=='Name of Contract'].index)].replace('\n',' ', regex=True)
        tmp1=tmp1[tmp1['Name of Contract']!='Name of Contract']
        tmp1=tmp1.reset_index()
        #print(str(i)) 
        tmp1=tmp1[['Name of Contract', 'Tendering Procedure','Contractor(s) & Address(es)', 'Amount(HK$)/ Contract Award Date']]

        tmp=pd.concat([tmp, tmp1]) #,ignore_index=True)
        tmp=tmp[['Name of Contract', 'Tendering Procedure','Contractor(s) & Address(es)', 'Amount(HK$)/ Contract Award Date']]

    #Export Formatting

    #export_ha=tmp.replace('\n',' ', regex=True)
    export_ha=tmp
    #export_ha=export_ha.reset_index(drop=True)
    #export_ha = export_ha.drop(['index'], axis=1)
    
    # if len(export_ha.columns)==6:
    #     export_ha[0:5].columns=['Name of Contract','Tendering Procedure','Contractor(s) & Address(es)','Amount(HK$)/ Contract Award Date','l1','l']
    #     export_ha = export_ha.drop(['l','l1'], axis=1)
    # else:   
    #     export_ha[0:4].columns=['Name of Contract','Tendering Procedure','Contractor(s) & Address(es)','Amount(HK$)/ Contract Award Date','l']
    #     export_ha = export_ha.drop(['l'], axis=1)

    export_ha=export_ha[export_ha['Name of Contract'].str.strip()!='Name of Contract']

    export_ha=export_ha.replace('\n',' ', regex=True)
    export_ha['Contractor(s)']=''
    export_ha['Address(es)']=''
    export_ha['Amount(HK$)']=''
    export_ha['Contract Award Date']=''

    export_ha=export_ha.reset_index()
    
    for i in range(len(export_ha)):
        try:
            export_ha.loc[i,'Contractor(s)']=export_ha['Contractor(s) & Address(es)'][i][:export_ha['Contractor(s) & Address(es)'][i].index('Limited')+7].strip()
            export_ha.loc[i,'Address(es)']=export_ha['Contractor(s) & Address(es)'][i][export_ha['Contractor(s) & Address(es)'][i].index('Limited')+7:].strip()
            #print(re.search(r'(\d+)\s(\d+)', export_ha['Amount(HK$)/ Contract Award Date'][i]))
            if re.search(r'(\d+)\s(\d+)', export_ha['Amount(HK$)/ Contract Award Date'][i])!=None:
                export_ha.loc[i,'Amount(HK$)']=export_ha['Amount(HK$)/ Contract Award Date'][i][:re.search(r'(\d+)\s(\d+)', export_ha['Amount(HK$)/ Contract Award Date'][i]).start()+2].strip()
                export_ha.loc[i,'Contract Award Date']=export_ha['Amount(HK$)/ Contract Award Date'][i][re.search(r'(\d+)\s(\d+)', export_ha['Amount(HK$)/ Contract Award Date'][i]).start()+2:].strip()
            else:
                export_ha.loc[i,'Amount(HK$)']=export_ha['Amount(HK$)/ Contract Award Date'][i][:re.search(r'(\d+)\s\(', export_ha['Amount(HK$)/ Contract Award Date'][i]).start()+2].strip()
                export_ha.loc[i,'Contract Award Date']=export_ha['Amount(HK$)/ Contract Award Date'][i][re.search(r'(\d+)\s\(', export_ha['Amount(HK$)/ Contract Award Date'][i]).start()+2:].strip()
            

        #export_ha['Amount']=export_ha
        except:
            pass

    final_export=export_ha[export_ha['Contractor(s) & Address(es)'].notna()]
    final_export=final_export[final_export['Contractor(s) & Address(es)']!='']
    final_export=final_export[final_export['Amount(HK$)']!='']
    final_export=final_export.reset_index(drop=True).drop(columns=['index']) 
    #print(final_export)

    final_export.to_csv('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/HA/'+export_file+'.csv', index=False, encoding="utf-8")

# im = page.to_image()

# im.debug_tablefinder({
#     "vertical_strategy": "lines",
#     "horizontal_strategy": "lines", 
#     "explicit_vertical_lines": df_v,#df_v,
#     "explicit_horizontal_lines":  df_h,#df_h_test,
#     "snap_tolerance": 3,
#     "join_tolerance": 3
# })



# In[1356]:


import pdfplumber

for string in [formatted_string,formatted_string_P1,formatted_string_P2,formatted_string_P3]:
    pdf_url="https://www.housingauthority.gov.hk/en/common/pdf/business-partnerships/tenders/BP_Tender_Award_"+string+".pdf"

    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_path = "BP_Tender_Award_"+string+".pdf"

        path_obj = Path(pdf_path)

        if not path_obj.exists():
            with open(pdf_path, "wb") as f:
                f.write(response.content)

            pdf_process(pdf_path,'HA_'+string)
            
        else:
            print(f"The file '{pdf_path}' already exists. Not writing to it.")

    except Exception as e:
        print(f"No File exists: {pdf_url}")




# In[ ]:




