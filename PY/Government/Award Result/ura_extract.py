#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os
os.chdir('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/URA')


# In[4]:


import pdfplumber
import requests
import pandas as pd

url = "https://www.ura.org.hk/f/page/2679/18828/(Published)%20Notice%20of%20Tender%20and%20Award%20-%20Works_2026.04-2026.06.pdf"

# 1. Download the PDF locally
response = requests.get(url)
with open("service_tender_notice.pdf", "wb") as f:
    f.write(response.content)

# 2. Extract Table Data
all_data = []

with pdfplumber.open("service_tender_notice.pdf") as pdf:
    for page in pdf.pages:
        # Extract tables from the page
        table = page.extract_table()
        if table:
            # The first row of the first page is usually the header
            all_data.extend(table)

# 3. Clean and Save to CSV
# We skip the first row if it's a header and convert to a DataFrame
df = pd.DataFrame(all_data[1:], columns=all_data[0])
df.to_csv("ura_awards_service.csv", index=False)

print("Data successfully extracted to ura_awards.csv")


# In[6]:


import pdfplumber
import requests
import pandas as pd

url = "https://www.ura.org.hk/f/page/2679/18828/(Published)%20Notice%20of%20Tender%20and%20Award%20-%20Services_2026.04-2026.06.pdf"

# 1. Download the PDF locally
response = requests.get(url)
with open("tender_notice.pdf", "wb") as f:
    f.write(response.content)

# 2. Extract Table Data
all_data = []

with pdfplumber.open("tender_notice.pdf") as pdf:
    for page in pdf.pages:
        # Extract tables from the page
        table = page.extract_table()
        if table:
            # The first row of the first page is usually the header
            all_data.extend(table)

# 3. Clean and Save to CSV
# We skip the first row if it's a header and convert to a DataFrame
df = pd.DataFrame(all_data[1:], columns=all_data[0])
df.to_csv("ura_awards_work.csv", index=False)

print("Data successfully extracted to ura_awards.csv")


# In[7]:


df


# In[13]:


import pandas as pd
import requests

url = "https://www.mtr.com.hk/en/corporate/tenders/Feb26.html"

# 1. Fetch the page content
header = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
response = requests.get(url, headers=header)

# 2. Use Pandas to find all tables on the page
# read_html returns a list of all tables found
tables = pd.read_html(response.text)

# 3. Identify the tender table (usually the first or only large table)
if tables:
    tender_df = tables[0]

    # Optional: Clean the data (e.g., removing newlines from addresses)
    tender_df = tender_df.replace(r'\n', ' ', regex=True)

    # 4. Save to CSV or Excel
    tender_df.to_csv("mtr_tenders_feb26.csv", index=False)
    print("Data extracted successfully!")
    print(tender_df.head())


# In[11]:


tender_df


# In[ ]:




