#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd


def millions_to_amount(value):
    """Convert source values expressed in HKD millions to numeric HKD."""
    if pd.isna(value):
        return None
    text = str(value).replace(',', '').strip()
    try:
        return float(text) * 1_000_000
    except ValueError:
        return value


# In[3]:


import os

from pathlib import Path

RUN_DATA_DIR = Path(os.environ["GOV_HERMES_DATA_DIR"]).resolve()
RUN_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.chdir(RUN_DATA_DIR)


# In[5]:


tmp=pd.DataFrame(columns=["ref","department","description","awardee","award_date",	"sum","period","url","start","end"])


# In[7]:


df_epd=pd.read_json('gov_epd.json',lines=True)


# In[13]:


df_epd_tmp=pd.concat([tmp, df_epd],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[17]:


from datetime import datetime

df_epd_tmp['award_date1']=pd.NaT

for i in range(len(df_epd_tmp)):
    if len(df_epd_tmp.loc[i,'award_date'])==8:
        df_epd_tmp.loc[i,'award_date1']=datetime.strptime(df_epd_tmp.loc[i,'award_date'], "%b %Y")
    elif len(df_epd_tmp.loc[i,'award_date'])>8:
        try:
            df_epd_tmp.loc[i,'award_date1']=datetime.strptime(df_epd_tmp.loc[i,'award_date'], "%B %Y")
        except:
            pass

df_epd_tmp['award_date']=df_epd_tmp['award_date1']


# In[19]:


df_epd_tmp=df_epd_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[21]:


df_dsd=pd.read_json('gov_dsd.json',lines=True)


# In[23]:


df_dsd_tmp=pd.concat([tmp, df_dsd],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[25]:


df_dsd_tmp['award_date1']=pd.NaT

for i in range(len(df_dsd_tmp)):
    df_dsd_tmp.loc[i,'award_date1']=datetime.strptime(df_dsd_tmp.loc[i,'award_date'], "%d %B %Y")
    df_dsd_tmp.loc[i,'start1']=datetime.strptime(df_dsd_tmp.loc[i,'start'], "%d %B %Y")
    df_dsd_tmp.loc[i,'end1']=datetime.strptime(df_dsd_tmp.loc[i,'end'], "%d %B %Y")

df_dsd_tmp['award_date']=df_dsd_tmp['award_date1']
df_dsd_tmp['start']=df_dsd_tmp['start1']
df_dsd_tmp['end']=df_dsd_tmp['end1']


# In[27]:


df_dsd_tmp=df_dsd_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[29]:


df_cedd=pd.read_json('gov_cedd.json',lines=True)


# In[31]:


df_cedd_tmp=pd.concat([tmp, df_cedd],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[33]:


df_cedd_tmp['award_date1']=pd.NaT

for i in range(len(df_cedd_tmp)):
    df_cedd_tmp.loc[i,'award_date1']=datetime.strptime(df_cedd_tmp.loc[i,'award_date'], "%d/%m/%Y")

df_cedd_tmp['award_date']=df_cedd_tmp['award_date1']


# In[35]:


df_cedd_tmp=df_cedd_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[37]:


df_cedd_consultant=pd.read_json('gov_cedd_consultant.json',lines=True)


# In[39]:


df_cedd_consultant_tmp=pd.concat([tmp, df_cedd_consultant],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[41]:


df_cedd_consultant_tmp['award_date1']=pd.NaT
df_cedd_consultant_tmp['start1']=pd.NaT
df_cedd_consultant_tmp['end1']=pd.NaT

for i in range(len(df_cedd_consultant_tmp)):
    df_cedd_consultant_tmp.loc[i,'award_date1']=datetime.strptime(df_cedd_consultant_tmp.loc[i,'award_date'], "%d/%m/%Y")
    df_cedd_consultant_tmp.loc[i,'start1']=datetime.strptime(df_cedd_consultant_tmp.loc[i,'start'], "%d/%m/%Y")
    df_cedd_consultant_tmp.loc[i,'end1']=datetime.strptime(df_cedd_consultant_tmp.loc[i,'end'], "%d/%m/%Y")


df_cedd_consultant_tmp['award_date']=df_cedd_consultant_tmp['award_date1']
df_cedd_consultant_tmp['start']=df_cedd_consultant_tmp['start1']
df_cedd_consultant_tmp['end']=df_cedd_consultant_tmp['end1']


# In[43]:


df_cedd_consultant_tmp=df_cedd_consultant_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[67]:


df_emsd=pd.read_json('gov_emsd.json',lines=True)


# In[69]:


df_emsd_tmp=pd.concat([tmp, df_emsd],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[71]:


df_emsd_tmp['award_date1']=pd.NaT
df_emsd_tmp['end1']=pd.NaT

for i in range(len(df_emsd_tmp)):
    df_emsd_tmp.loc[i,'award_date1']=datetime.strptime(df_emsd_tmp.loc[i,'award_date'], "%d %B %Y")
    df_emsd_tmp.loc[i,'end1']=datetime.strptime(df_emsd_tmp.loc[i,'end'], "%d %B %Y")


df_emsd_tmp['award_date']=df_emsd_tmp['award_date1']
df_emsd_tmp['end']=df_emsd_tmp['end1']


# In[73]:


df_emsd_tmp=df_emsd_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[279]:


df_emsd_construction=pd.read_json('gov_emsd_construction.json',lines=True)


# In[281]:


df_emsd_construction_tmp=pd.concat([tmp, df_emsd_construction],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[283]:


df_emsd_construction_tmp['award_date1']=pd.NaT

for i in range(len(df_emsd_construction_tmp)):
    df_emsd_construction_tmp.loc[i,'award_date1']=datetime.strptime(df_emsd_construction_tmp.loc[i,'award_date'], "%b %Y")


df_emsd_construction_tmp['award_date']=df_emsd_construction_tmp['award_date1']


# In[285]:


df_emsd_construction_tmp=df_emsd_construction_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[61]:


df_hkaa=pd.read_json('gov_hkaa.json',lines=True)


# In[63]:


df_hkaa_tmp=pd.concat([tmp, df_hkaa],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[87]:


df_hkaa_tmp['award_date1']=pd.NaT
df_hkaa_tmp['sum1']=pd.Series([None]*len(df_hkaa_tmp), dtype='object')

for i in range(len(df_hkaa_tmp)):
    df_hkaa_tmp.loc[i,'award_date1']=datetime.strptime(df_hkaa_tmp.loc[i,'award_date'], "%Y-%m-%d")
    if 'amount' in df_hkaa_tmp.loc[i,'sum']:
        df_hkaa_tmp.loc[i,'sum1']=df_hkaa_tmp.loc[i,'sum']['amount']
    else:
        df_hkaa_tmp.loc[i,'sum1']=df_hkaa_tmp.loc[i,'sum']

df_hkaa_tmp['award_date']=df_hkaa_tmp['award_date1']
df_hkaa_tmp['sum']=df_hkaa_tmp['sum1']


# In[91]:


df_hkaa_tmp=df_hkaa_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[94]:


df_hyd=pd.read_json('gov_hyd.json',lines=True)


# In[96]:


df_hyd_tmp=pd.concat([tmp, df_hyd],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[102]:


df_hyd_tmp['award_date1']=pd.NaT
df_hyd_tmp['sum1']=pd.Series([None]*len(df_hyd_tmp), dtype='object')

for i in range(len(df_hyd_tmp)):
    df_hyd_tmp.loc[i,'award_date1']=datetime.strptime(df_hyd_tmp.loc[i,'award_date'], "%d/%m/%Y")
    df_hyd_tmp.loc[i,'sum1']=millions_to_amount(df_hyd_tmp.loc[i,'sum'])

df_hyd_tmp['award_date']=df_hyd_tmp['award_date1']
df_hyd_tmp['sum']=df_hyd_tmp['sum1']


# In[104]:


df_hyd_tmp=df_hyd_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[119]:


df_wsd=pd.read_json('gov_wsd.json',lines=True)


# In[121]:


df_wsd_tmp=pd.concat([tmp, df_wsd],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[125]:


df_wsd_tmp['award_date1']=pd.NaT
df_wsd_tmp['sum1']=pd.Series([None]*len(df_wsd_tmp), dtype='object')
df_wsd_tmp['start1']=pd.NaT
df_wsd_tmp['end1']=pd.NaT

for i in range(len(df_wsd_tmp)):
    df_wsd_tmp.loc[i,'award_date1']=datetime.strptime(df_wsd_tmp.loc[i,'award_date'], "%d %b %Y")
    df_wsd_tmp.loc[i,'sum1']=millions_to_amount(df_wsd_tmp.loc[i,'sum'])
    df_wsd_tmp.loc[i,'start1']=datetime.strptime(df_wsd_tmp.loc[i,'start'], "%d %b %Y")
    df_wsd_tmp.loc[i,'end1']=datetime.strptime(df_wsd_tmp.loc[i,'end'], "%b %Y")

df_wsd_tmp['award_date']=df_wsd_tmp['award_date1']
df_wsd_tmp['sum']=df_wsd_tmp['sum1']
df_wsd_tmp['end']=df_wsd_tmp['end1']
df_wsd_tmp['start']=df_wsd_tmp['start1']


# In[127]:


df_wsd_tmp=df_wsd_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[137]:


df_wsd_consultant=pd.read_json('gov_wsd_consultant.json',lines=True)


# In[141]:


df_wsd_consultant_tmp=pd.concat([tmp, df_wsd_consultant],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[149]:


df_wsd_consultant_tmp['award_date1']=pd.NaT
df_wsd_consultant_tmp['end1']=pd.NaT

for i in range(len(df_wsd_consultant_tmp)):
    try:
        df_wsd_consultant_tmp.loc[i,'award_date1']=datetime.strptime(df_wsd_consultant_tmp.loc[i,'award_date'], "%d/%m/%Y")
    except:
        pass
    try:
        df_wsd_consultant_tmp.loc[i,'end1']=datetime.strptime(df_wsd_consultant_tmp.loc[i,'end'], "%d/%m/%Y")
    except:
        pass

df_wsd_consultant_tmp['award_date']=df_wsd_consultant_tmp['award_date1']
df_wsd_consultant_tmp['end']=df_wsd_consultant_tmp['end1']


# In[153]:


df_wsd_consultant_tmp=df_wsd_consultant_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[167]:


df_td=pd.read_json('gov_td.json',lines=True)


# In[169]:


df_td_tmp=pd.concat([tmp, df_td],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[173]:


df_td_tmp['award_date1']=pd.NaT
df_td_tmp['sum1']=pd.Series([None]*len(df_td_tmp), dtype='object')

for i in range(len(df_td_tmp)):
    try:
        df_td_tmp.loc[i,'award_date1']=datetime.strptime(df_td_tmp.loc[i,'award_date'], "%d.%m.%Y")
    except:
        pass

    df_td_tmp.loc[i,'sum1']=millions_to_amount(df_td_tmp.loc[i,'sum'])


df_td_tmp['award_date']=df_td_tmp['award_date1']
df_td_tmp['sum']=df_td_tmp['sum1']


# In[175]:


df_td_tmp=df_td_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[187]:


df_td_consultant=pd.read_json('gov_td_consultant.json',lines=True)


# In[189]:


df_td_consultant_tmp=pd.concat([tmp, df_td_consultant],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[191]:


df_td_consultant_tmp['award_date1']=pd.NaT
df_td_consultant_tmp['sum1']=pd.Series([None]*len(df_td_consultant_tmp), dtype='object')

for i in range(len(df_td_consultant_tmp)):
    try:
        df_td_consultant_tmp.loc[i,'award_date1']=datetime.strptime(df_td_consultant_tmp.loc[i,'award_date'], "%d.%m.%Y")
    except:
        pass

    df_td_consultant_tmp.loc[i,'sum1']=millions_to_amount(df_td_consultant_tmp.loc[i,'sum'])


df_td_consultant_tmp['award_date']=df_td_consultant_tmp['award_date1']
df_td_consultant_tmp['sum']=df_td_consultant_tmp['sum1']


# In[193]:


df_td_consultant_tmp=df_td_consultant_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[195]:


df_wsd=pd.read_json('gov_wsd.json',lines=True)


# In[200]:


df_wsd_tmp=pd.concat([tmp, df_wsd],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[202]:


df_wsd_tmp['award_date1']=pd.NaT
df_wsd_tmp['sum1']=pd.Series([None]*len(df_wsd_tmp), dtype='object')
df_wsd_tmp['start1']=pd.NaT
df_wsd_tmp['end1']=pd.NaT

for i in range(len(df_wsd_tmp)):
    try:
        df_wsd_tmp.loc[i,'award_date1']=datetime.strptime(df_wsd_tmp.loc[i,'award_date'], "%d %b %Y")
        df_wsd_tmp.loc[i,'start1']=datetime.strptime(df_wsd_tmp.loc[i,'start'], "%d %b %Y")
        df_wsd_tmp.loc[i,'end1']=datetime.strptime(df_wsd_tmp.loc[i,'end'], "%b %Y")
    except:
        pass

    df_wsd_tmp.loc[i,'sum1']=millions_to_amount(df_wsd_tmp.loc[i,'sum'])


df_wsd_tmp['award_date']=df_wsd_tmp['award_date1']
df_wsd_tmp['sum']=df_wsd_tmp['sum1']
df_wsd_tmp['start']=df_wsd_tmp['start1']
df_wsd_tmp['end']=df_wsd_tmp['end1']


# In[204]:


df_wsd_tmp=df_wsd_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[216]:


df_wsd_consultant=pd.read_json('gov_wsd_consultant.json',lines=True)


# In[228]:


df_wsd_consultant_tmp=pd.concat([tmp, df_wsd_consultant],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[234]:


df_wsd_consultant_tmp['award_date1']=pd.NaT
df_wsd_consultant_tmp['sum1']=pd.Series([None]*len(df_wsd_consultant_tmp), dtype='object')
df_wsd_consultant_tmp['start1']=pd.NaT
df_wsd_consultant_tmp['end1']=pd.NaT

for i in range(len(df_wsd_consultant_tmp)):
    try:
        df_wsd_consultant_tmp.loc[i,'award_date1']=datetime.strptime(df_wsd_consultant_tmp.loc[i,'award_date'], "%d %b %Y")
        df_wsd_consultant_tmp.loc[i,'start1']=datetime.strptime(df_wsd_consultant_tmp.loc[i,'start'], "%d %b %Y")
        df_wsd_consultant_tmp.loc[i,'end1']=datetime.strptime(df_wsd_consultant_tmp.loc[i,'end'], "%b %Y")
    except:
        pass

    df_wsd_consultant_tmp.loc[i,'sum1']=df_wsd_consultant_tmp.loc[i,'sum']


df_wsd_consultant_tmp['award_date']=df_wsd_consultant_tmp['award_date1']
df_wsd_consultant_tmp['sum']=df_wsd_consultant_tmp['sum1']
df_wsd_consultant_tmp['start']=df_wsd_consultant_tmp['start1']
df_wsd_consultant_tmp['end']=df_wsd_consultant_tmp['end1']


# In[238]:


df_wsd_consultant_tmp=df_wsd_consultant_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[250]:


df_gld=pd.read_json('gov_gld.json',lines=True)


# In[260]:


df_gld['description']=df_gld['particulars']
df_gld_tmp=pd.concat([tmp, df_gld],axis=0)[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]

df_gld_tmp=df_gld_tmp[df_gld_tmp['award_date'].isnull()==False]


# In[270]:


df_gld_tmp['award_date1']=pd.NaT

for i in range(len(df_gld_tmp)):
    try:
        df_gld_tmp.loc[i,'award_date1']=datetime.strptime(df_gld_tmp.loc[i,'award_date'], "%d %b %Y")
    except:
        pass


df_gld_tmp['award_date']=df_gld_tmp['award_date1']


# In[272]:


df_gld_tmp=df_gld_tmp[["ref","department","description","awardee","award_date",	"sum","period","url","start","end"]]


# In[262]:





# In[287]:


tmp_export=pd.concat([tmp,df_epd_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_dsd_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_cedd_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_cedd_consultant_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_emsd_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_emsd_construction_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_hkaa_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_hyd_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_wsd_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_wsd_consultant_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_td_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_td_consultant_tmp], axis=0)
tmp_export=pd.concat([tmp_export,df_gld_tmp], axis=0)

# Canonical source provenance and exact-row deduplication for the dry run.
from urllib.parse import urljoin
relative_url = tmp_export['url'].fillna('').astype(str).str.startswith('/')
tmp_export.loc[relative_url, 'url'] = tmp_export.loc[relative_url, 'url'].map(
    lambda value: urljoin('https://www.emsd.gov.hk', str(value))
)
hyd_contract = tmp_export['department'].eq('Highways Department')
tmp_export.loc[hyd_contract & tmp_export['url'].isna(), 'url'] = (
    'https://www.hyd.gov.hk/en/tender_notices/contracts/awarded/index.html'
)
hyd_consultant = tmp_export['department'].eq('hyd')
tmp_export.loc[hyd_consultant, 'department'] = 'Highways Department'
tmp_export.loc[hyd_consultant, 'url'] = (
    'https://www.hyd.gov.hk/en/tender_notices/consultancies/awarded/index.html'
)
wsd_missing_url = tmp_export['department'].eq('Water Supplies Department') & tmp_export['url'].isna()
tmp_export.loc[wsd_missing_url, 'url'] = (
    'https://www.wsd.gov.hk/en/tenders-contracts-and-consultancies/consultancies/'
    'award-consultancies/index.html'
)
tmp_export = tmp_export.replace(r'^\s*$', pd.NA, regex=True)
tmp_export = tmp_export.dropna(subset=['ref', 'description', 'awardee', 'sum'], how='all')
tmp_export = tmp_export.drop_duplicates(ignore_index=True)


# In[289]:


tmp_export.head()


# In[291]:


from datetime import date
date_string=date.today().strftime("%b%Y")

OUTPUT_FILE = Path(os.environ["GOV_HERMES_OUTPUT_FILE"]).resolve()
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
tmp_export.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")


# In[ ]:




