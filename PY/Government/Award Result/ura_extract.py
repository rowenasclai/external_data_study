#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os
os.chdir('/Users/rowena/Other Projects/external_data_study/Result/Government Contract Extraction/URA')


# In[4]:


import pdfplumber
import requests
import pandas as pd

import requests
from bs4 import BeautifulSoup

url="https://www.ura.org.hk/tc/announcement-and-notices/notice-of-awarded-agreement-contract"
response = requests.get(url)



domain="https://www.ura.org.hk/"
soup = BeautifulSoup(response.text, "html.parser")

container = soup.find("div", class_="ckec")

results = []

if container:
    for li in container.find_all("li"):
# Extract the category name (e.g. '工程合約', '服務合約')
        category = li.contents[0].get_text(strip=True) if hasattr(li.contents[0], 'get_text') else str(li.contents[0]).strip()
    # Look for the hyperlink
        link_tag = li.find("a", href=True)
        if link_tag:
            link_text = link_tag.get_text(strip=True)
            full_url = domain+link_tag["href"]
            results.append({
                "category": category,
                "label": link_text,
                "url": full_url
            })
        else:
        # Handle cases where there is no contract link
            status_text = li.get_text(strip=True)
            results.append({
            "category": category,
            "label": "None",
            "url": None,
            "notes": status_text
            })

for i in range(len(results)):
    if results[i]['category']=='工程合約':
        award_url=results[i]['url']
    elif results[i]['category']=='服務合約':
        service_url=results[i]['url']


#url = "https://www.ura.org.hk/f/page/2679/18828/(Published)%20Notice%20of%20Tender%20and%20Award%20-%20Works_2026.04-2026.06.pdf"
url=award_url

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

from datetime import datetime
from dateutil.relativedelta import relativedelta

current_datetime = datetime.now()
past_1_month = current_datetime  - relativedelta(months=1)
formatted_string_P1 = past_1_month.strftime("%b%Y")

# 3. Clean and Save to CSV
# We skip the first row if it's a header and convert to a DataFrame
df = pd.DataFrame(all_data[1:], columns=all_data[0])
df.to_csv("ura_awards_service_"+formatted_string_P1+".csv", index=False)

print("Data successfully extracted to ura_awards_"+formatted_string_P1+".csv")


# In[6]:


import pdfplumber
import requests
import pandas as pd

#url = "https://www.ura.org.hk/f/page/2679/18828/(Published)%20Notice%20of%20Tender%20and%20Award%20-%20Services_2026.04-2026.06.pdf"
url=service_url

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
df.to_csv("ura_awards_work_"+formatted_string_P1+".csv", index=False)

print("Data successfully extracted to ura_service_"+formatted_string_P1+".csv")


# In[7]:





