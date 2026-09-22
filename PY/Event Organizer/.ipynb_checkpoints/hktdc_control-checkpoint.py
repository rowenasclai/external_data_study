#!/usr/bin/env python
# coding: utf-8

# In[3]:


import pandas as pd


# In[4]:


df=pd.read_csv('/Users/rowena/Other Projects/external_data_study/Result/Exhibition Organizers/HKTDC/Event_Schedule/event_control.csv')


# In[13]:


today = pd.Timestamp.now().normalize()  # .normalize() sets time to 00:00:00
start_day = today + pd.Timedelta(days=30)
week_t2 = today + pd.Timedelta(days=14)
day_10 = today + pd.Timedelta(days=10)
week_1 = today + pd.Timedelta(days=7)
day_3 = today + pd.Timedelta(days=3)

df['event_start_date'] = pd.to_datetime(df['event_start_date'])

df[((df['event_start_date'] == start_day) | (df['event_start_date']== week_t2) |(df['event_start_date']== day_10) |(df['event_start_date']==week_1) |(df['event_start_date']==day_3)) & (df['event_start_date'] > today)]


# In[14]:


tmp=df[((df['event_start_date']< start_day) | (df['event_start_date']== week_t2) |(df['event_start_date']== day_10) |(df['event_start_date']==week_1) |(df['event_start_date']==day_3)) & (df['event_start_date'] > today)]


# In[32]:


import subprocess

#all_events=['hkelectronicsfairae']

all_events=list(tmp['prefix'])
# The text input you want to send into the Python script

for t in all_events:
#my_text_input = "hello from the parent process"

# Execute the python script as a subprocess
    result_l1 = subprocess.run(
        ["python3", "/Users/rowena/Other Projects/external_data_study/PY/Event Organizer/hktdc_exhibit_L1.py"],
        input=t,
        text=True,
        capture_output=True
    )

    if result_l1.returncode != 0:
        print(f"❌ L1 執行失敗！錯誤訊息如下：\n{result_l1.stderr}")
        break # 失敗就先停止，方便排查
    else:
        print(f"✅ L1 執行成功。標準輸出：\n{result_l1.stdout}")

    result_l2 = subprocess.run(
        ["python3", "/Users/rowena/Other Projects/external_data_study/PY/Event Organizer/hktdc_exhibit_L2.py"],
        input=t,
        text=True,
        capture_output=True
    )

    if result_l2.returncode != 0:
        print(f"❌ L2 執行失敗！錯誤訊息如下：\n{result_l2.stderr}")
        break # 失敗就先停止，方便排查
    else:
        print(f"✅ L2 執行成功。標準輸出：\n{result_l2.stdout}")

    result_l3 = subprocess.run(
        ["python3", "/Users/rowena/Other Projects/external_data_study/PY/Event Organizer/hktdc_exhibit_L3.py"],
        input=t,
        text=True,
        capture_output=True
    )

    if result_l3.returncode != 0:
        print(f"❌ L3 執行失敗！錯誤訊息如下：\n{result_l3.stderr}")
        break # 失敗就先停止，方便排查
    else:
        print(f"✅ L3 執行成功。標準輸出：\n{result_l3.stdout}")

    result_format = subprocess.run(
        ["python3", "/Users/rowena/Other Projects/external_data_study/PY/Event Organizer/hktdc_format.py"],
        input=t,
        text=True,
        capture_output=True
    )

# In[30]:


int(1449/20)


# In[ ]:




