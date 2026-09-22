#!/usr/bin/env python
# coding: utf-8

# In[7]:


import re
import os

import json
import pandas as pd


# In[8]:


prefix=input('What is the prefix of your exhibition?')
os.chdir("/Users/rowena/Other Projects/external_data_study/Result/Exhibition Organizers/HKTDC/") 
os.makedirs(prefix, exist_ok=True)
os.chdir("/Users/rowena/Other Projects/external_data_study/Result/Exhibition Organizers/HKTDC/"+prefix) 


# In[9]:


file_name='hktdc_'+prefix+'_L1.csv'
df1 = pd.read_csv(file_name, low_memory=False,header=0,delimiter=",")

file_name='hktdc_'+prefix+'_L2.csv'
df2 = pd.read_csv(file_name, low_memory=False,header=0,delimiter=",")


file_name='hktdc_'+prefix+'_L3.csv'
df3 = pd.read_csv(file_name, low_memory=False,header=0,delimiter=",")


# In[10]:


df1['exhibitor_url']='https://www.hktdc.com'+df1['url']
tmp = pd.merge(df1, df2, on='exhibitor_url', how='left', suffixes=('', '_L2'))

df=pd.merge(tmp, df3, left_on='supplier_url', right_on='url',how='left', suffixes=('', '_L3'))


# In[11]:


df=df.drop(columns=['company name','location'])
df = df.replace(r'\n',' ', regex=True)
df = df.replace(r'\r+|\n+|\t+','', regex=True)


# In[12]:


df.to_csv('imp_hktdc_'+prefix+'.csv', index=False, encoding='utf-8')


# In[ ]:




