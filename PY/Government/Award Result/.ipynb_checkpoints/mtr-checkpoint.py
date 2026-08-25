#!/usr/bin/env python
# coding: utf-8

# In[1]:


#from seleniumbase import Driver
from PIL import Image
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import csv, time, re, math

import requests


# In[2]:


from datetime import datetime
from datetime import datetime, timedelta

# Approximation (30 days * 2)
#two_months_ago = datetime.now() - timedelta(days=60)

#print(two_months_ago)


current_datetime = datetime.now()
current_datetime = datetime.now()- timedelta(days=60)

# Format as "YYYY-MM-DD HH:MM:SS"
formatted_string = current_datetime.strftime("%b%y")

#print(formatted_string)

#formatted_string="Feb26"


# In[13]:


url="https://www.mtr.com.hk/en/corporate/tenders/"+formatted_string+".html"

try:

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

except requests.exceptions.HTTPError as errh:
    #target_table=pd.DataFrame()
    pass


# In[16]:


# 1. Locate ALL <table> elements on the page
all_tables = soup.find_all('table')

# 2. Select the specific table by its position (index)
# --- IMPORTANT: You will need to try different indices (0, 1, 2, etc.) ---

# Example: If the tender data is in the FIRST table:
if all_tables:
    target_table = all_tables[0] 
elif len(all_tables) > 1:
    # Example: If the tender data is in the SECOND table (index 1):
    target_table = all_tables[1]
else:
    target_table =pd.DataFrame()


# In[5]:


import requests
from bs4 import BeautifulSoup

def handle_merged_table_rows(table_element):
    """
    Parses an HTML table, handling cells merged with 'rowspan' and 'colspan'.

    Args:
        table_element: The BeautifulSoup tag object for the <table>.

    Returns:
        A list of lists, where each inner list is a full, non-merged row.
    """
    rows = table_element.find_all('tr')

    # 1. Initialize the virtual grid
    # This list will track which slots in each row are already filled by a spanned cell.
    grid = []

    for row_index, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        cell_index = 0

        # Ensure the current row has a placeholder in the grid
        if len(grid) <= row_index:
            grid.append([])

        for cell in cells:
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            cell_text = cell.get_text(strip=True)

            # 2. Find the first available column slot in the current row
            while len(grid[row_index]) > cell_index and grid[row_index][cell_index] is not None:
                cell_index += 1

            # 3. Fill the current slot(s) and mark subsequent slots as occupied
            for i in range(rowspan):
                current_row = row_index + i

                # Ensure the target row exists in the grid
                while len(grid) <= current_row:
                    grid.append([None] * cell_index) # Pad with None up to the current column

                # Pad the current row if needed
                while len(grid[current_row]) < cell_index + colspan:
                    grid[current_row].append(None)

                # Place the cell text across the column span (horizontal merge)
                for j in range(colspan):
                    # For the first row (i=0), we put the content.
                    # For subsequent rows (i>0), we simply mark the space as occupied (None).
                    if i == 0:
                        grid[current_row][cell_index + j] = cell_text
                    else:
                        # This marks the space as 'taken' by a rowspan cell from an earlier row
                        grid[current_row][cell_index + j] = None 

            # Advance the column index by the colspan amount
            cell_index += colspan

    # 4. Clean up the grid: Replace 'None' (occupied slots) with the value
    #    from the cell that spans into them (this handles the rowspan values).
    final_data = []
    for r_idx, grid_row in enumerate(grid):
        processed_row = []
        for c_idx, cell_value in enumerate(grid_row):
            if cell_value is None:
                # Look upwards to find the cell that spanned into this slot
                # This assumes the spanned cell value should be copied down
                for prev_r_idx in range(r_idx - 1, -1, -1):
                    # Check if the cell above exists and is the one that spanned down
                    if c_idx < len(grid[prev_r_idx]) and grid[prev_r_idx][c_idx] is not None:
                         # We found the spanning value; copy it to the current cell
                         cell_value = grid[prev_r_idx][c_idx]
                         break

            # Handle cells that were marked as occupied but didn't have a direct spanning value
            # (This is mostly a safeguard, the previous logic should cover it)
            if cell_value is None:
                cell_value = '' # Default to empty string if no content is found

            processed_row.append(cell_value)

        # Only add the row if it contains data (not just empty placeholders)
        if any(processed_row):
            final_data.append(processed_row)

    return final_data

# --- How to use this function with your MTR script: ---

# ... (code to fetch page and find the target_table) ...

# if target_table:
#     extracted_data = handle_merged_table_rows(target_table)
#     
#     # Now you have clean, rectangular data ready for a pandas DataFrame:
#     # df = pd.DataFrame(extracted_data[1:], columns=extracted_data[0]) 
#     # print(df)


# In[24]:


target_table.empty


# In[26]:


if target_table.empty==False:
    extracted_data = handle_merged_table_rows(target_table)
    tmp_df=pd.DataFrame(extracted_data)
    tmp=pd.DataFrame(tmp_df.iloc[1:,:])
    tmp.columns=list(tmp_df.iloc[0,:])

    df_mtr=tmp


# In[27]:


# A list of legal suffixes (ensure they are in all caps for easy matching)
SUFFIX_KEYWORDS = [
    'LIMITED', 'LTD', 'COMPANY', 'CO.', 'CORPORATION', 'CORP', 
    'INC', 'GROUP', 'HONG KONG', 'SAR', 'LLC', 
    'PTE LTD', 'PLC', '&' # Ampersand is often a key name component
]

def extract_name_by_suffix(text):
    if not isinstance(text, str) or not text.strip():
        return (None, None) # Return None for empty/invalid input

    # Standardize the text for searching (makes matching easier)
    upper_text = text.upper()

    # Find the position of the last occurring key suffix
    last_suffix_index = -1
    found_suffix_length = 0

    for suffix in SUFFIX_KEYWORDS:
        # We look for the suffix followed by a space or end-of-string 
        # to avoid matching 'Limited' inside a word.
        search_term = suffix + ' '

        # Use rfind to find the LAST occurrence of the suffix in the string
        index = upper_text.rfind(search_term)

        if index > last_suffix_index:
            last_suffix_index = index
            found_suffix_length = len(search_term) - 1 # Length of the word itself

    # --- Separation Logic ---

    if last_suffix_index != -1:
        # The split point is AFTER the last found suffix
        split_end_index = last_suffix_index + found_suffix_length

        # Company Name: Everything up to (and including) the suffix and one following word (optional space)
        contractor_name = text[:split_end_index].strip()

        # Address: The rest of the string
        address = text[split_end_index:].strip().lstrip(',; ')

        # Fallback check: Sometimes the suffix is the last word in the name,
        # and the address starts after the next space.
        if address and not address[0].isdigit() and any(c in address.upper() for c in ['RD', 'ST', 'FL']):
             # Address starts cleanly with a number or address indicator, so the split is good.
             pass
        elif address and contractor_name and len(contractor_name.split()) < 2:
             # If the name is too short, the split might be wrong, but we prioritize the suffix rule.
             pass

    else:
        # If no key suffix is found, assume the first part is the company name 
        # and try to split by the first comma or a maximum of 4 words.
        parts = text.split(',', 1)
        if len(parts) > 1:
            contractor_name = parts[0].strip()
            address = parts[1].strip()
        else:
            # Final fallback: Assume the entire string is the contractor name
            contractor_name = text.strip()
            address = ''

    return (contractor_name, address)


# In[31]:


try:

# Assuming your clean DataFrame from the previous step is named 'df'
    formatted_file_string = current_datetime.strftime("%Y-%m-01")
# Apply the function to the 'Contractor' column and create two new columns
    df_mtr[['Contractor Name', 'Address']] = df_mtr['Contractor(s) and Address(es)'].apply(lambda x: pd.Series(extract_name_by_suffix(x)))
    df_mtr['Month']=formatted_file_string

    final_df=pd.DataFrame([])

    final_df=pd.concat([df_mtr, final_df], axis=0)
except:
    final_df=pd.DataFrame([])
    pass
# You now have two new columns with the separated data
#print(df[['Contractor', 'Contractor Name', 'Address']].head())


# In[32]:


if len(final_df):
    final_df.to_csv('/Users/rowena/Other Projects/external_data_study/Result/mtr/mtr_'+formatted_string+'.csv', index=False, encoding="utf-8") 


# In[ ]:




