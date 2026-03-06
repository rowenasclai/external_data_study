#!/usr/bin/env python
# coding: utf-8

# In[6]:


import pdfplumber
import pandas as pd
import requests
import io
import re
import os

import camelot.io as camelot


# In[155]:


settings = {
    "explicit_vertical_lines": [ 10,410, 530, 690,810 ],
    "explicit_horizontal_lines": [ 180,210, 290,380,470,580],
    "horizontal_strategy": "lines", 
    "snap_tolerance": 3,
    "join_tolerance": 5
}

with pdfplumber.open("BP_Tender_Award_Jan_2026.pdf") as pdf:
    page = pdf.pages[0]
    # Apply the custom settings
    table = page.extract_table(table_settings=settings)
#table = page[0].extract_table(table_settings=settings)


# In[156]:


tmp=pd.DataFrame(table,columns=table[0])


# In[157]:


settings = {
    "explicit_vertical_lines": [ 10,410, 530, 690,810 ],
    "explicit_horizontal_lines": [ 20,80,170, 250,340,420,580],
    "horizontal_strategy": "lines", 
    "snap_tolerance": 3,
    "join_tolerance": 5
}

all_data = table

with pdfplumber.open("BP_Tender_Award_Jan_2026.pdf") as pdf:
    page = pdf.pages[1]
    # Apply the custom settings
    table = page.extract_table(table_settings=settings)
    tmp1=pd.DataFrame(table,columns=table[0])
    tmp=pd.concat([tmp, tmp1])
        #all_data.append(table)
    


# In[165]:


settings = {
    "explicit_vertical_lines": [ 10,410, 530, 690,810 ],
    "explicit_horizontal_lines": [ 60,90,190, 300,390,580],
    "horizontal_strategy": "lines", 
    "snap_tolerance": 3,
    "join_tolerance": 5
}

all_data = table

with pdfplumber.open("BP_Tender_Award_Jan_2026.pdf") as pdf:
    page = pdf.pages[2]
    # Apply the custom settings
    table = page.extract_table(table_settings=settings)
    tmp1=pd.DataFrame(table,columns=table[0])
    tmp=pd.concat([tmp, tmp1])
        #all_data.append(table)
    


# In[180]:


settings = {
    "explicit_vertical_lines": [ 10,410, 530, 690,810 ],
    "explicit_horizontal_lines": [ 20,80,170, 280,390,480,580],
    "horizontal_strategy": "lines", 
    "snap_tolerance": 3,
    "join_tolerance": 5
}

all_data = table

with pdfplumber.open("BP_Tender_Award_Jan_2026.pdf") as pdf:
    page = pdf.pages[4]
    # Apply the custom settings
    table = page.extract_table(table_settings=settings)
    tmp1=pd.DataFrame(table,columns=table[0])
    tmp=pd.concat([tmp, tmp1])
        #all_data.append(table)
    


# In[181]:


tmp


# In[187]:


export_ha=tmp.replace('\n',' ', regex=True)

export_ha=export_ha[export_ha['Name of Contract'].str.strip()!='Name of Contract']


# In[190]:


export_ha.columns=export_ha.columns.str.replace('\n',' ', regex=True)


# In[191]:


export_ha


# In[233]:


for i in range(len(export_ha)):
    try:
        export_ha.loc[i,'Contractor(s)']=export_ha['Contractor(s) & Address(es)'][i][:export_ha['Contractor(s) & Address(es)'][i].index('Limited')+7].strip()
        export_ha.loc[i,'Address(es)'][i]=export_ha['Contractor(s) & Address(es)'][i][export_ha['Contractor(s) & Address(es)'][i].index('Limited')+7:].strip()
        export_ha.loc[i,'Amount(HK$)']=export_ha['Amount(HK$)/ Contract Award Date'][i][:re.search(r'(\d+)\s(\d+)', export_ha['Amount(HK$)/ Contract Award Date'][0]).start()+2].strip()
        export_ha.loc[i,'Contract Award Date']=export_ha['Amount(HK$)/ Contract Award Date'][i][re.search(r'(\d+)\s(\d+)', export_ha['Amount(HK$)/ Contract Award Date'][0]).start()+2:].strip()

        #export_ha['Amount']=export_ha
    except:
        pass


# In[235]:


export_ha=export_ha.reset_index()


# In[237]:


export_ha = export_ha.drop(['level_0','index'], axis=1)


# In[239]:


export_ha.to_csv('/Users/rowena/Other Projects/external_data_study/Result/HA/ha_Jan2026.csv', index=False, encoding="utf-8") 


# In[179]:


import pdfplumber
pdf = pdfplumber.open("BP_Tender_Award_Jan_2026.pdf") # See note below
page = pdf.pages[4]
im = page.to_image()

im.debug_tablefinder({
    "explicit_vertical_lines": [ 10,410, 530, 690,810 ],
    "explicit_horizontal_lines": [ 20,80,170, 280,390,480,580],
    "horizontal_strategy": "lines", 
    "snap_tolerance": 3,
    "join_tolerance": 5
})


# In[ ]:




