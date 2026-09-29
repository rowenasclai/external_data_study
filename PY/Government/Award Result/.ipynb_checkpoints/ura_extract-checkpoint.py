#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os
os.chdir('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/URA')


# In[4]:


import pdfplumber
import requests
import pandas as pd

#url = "https://www.ura.org.hk/f/page/2679/18828/(Published)%20Notice%20of%20Tender%20and%20Award%20-%20Works_2026.04-2026.06.pdf"
url="https://www.ura.org.hk/f/page/2679/18998/(Published)%20Notice%20of%20Tender%20and%20Award%20-%20Works_2026.06-2026.08.pdf"

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

#url = "https://www.ura.org.hk/f/page/2679/18828/(Published)%20Notice%20of%20Tender%20and%20Award%20-%20Services_2026.04-2026.06.pdf"
url="https://www.ura.org.hk/f/page/2679/18998/(Published)%20Notice%20of%20Tender%20and%20Award%20-%20Services_2026.06-2026.08.pdf"

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





