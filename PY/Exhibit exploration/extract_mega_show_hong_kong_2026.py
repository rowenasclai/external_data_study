#!/usr/bin/env python3
"""Extract public MEGA SHOW Hong Kong 2026 Part 1 exhibitor records."""
from __future__ import annotations
import argparse,csv,json,time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
API='https://api.comasia.net.cn/web/api/v1/exhibitor/index'
CODE='29ebacf3'; CATEGORIES=('13','22','4','183','1117','249','420','1560-1561-1565'); PAGE_SIZE=12
FIELDS=['exhibitor_id','event_id','company_name','booth_no','category_ids','logo_url','profile_url','source_url','source_position']
def get(category,page):
 u=API+'?'+urlencode({'code':CODE,'cid1':category,'page':page})
 with urlopen(Request(u,headers={'User-Agent':'external-data-study/1.0'}),timeout=30) as r:d=json.load(r)
 if d.get('code')!=200 or not isinstance(d.get('data',{}).get('list'),list):raise ValueError(f'bad response {category}/{page}')
 return d['data']['list'],u
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--json-output',required=True);a=p.parse_args(); rows=[]
 for cat in CATEGORIES:
  for page in range(1,1000):
   items,url=get(cat,page)
   for i in items:
    if not i.get('id') or not str(i.get('name') or '').strip():raise ValueError('missing ID/name')
    rows.append({'exhibitor_id':str(i['id']),'event_id':str(i.get('hid') or ''),'company_name':i['name'].strip(),'booth_no':i.get('booth_no') or '','category_ids':[cat],'logo_url':i.get('thumb') or '','profile_url':f'https://megashow.comasia.net.cn/index/exhibitor-info.html?id={i["id"]}','source_url':url})
   if len(items)<PAGE_SIZE:break
   time.sleep(.12)
  else:raise ValueError('pagination limit exceeded')
 # Categories are overlapping filters, not separate exhibitor identities.
 # Collapse identical source IDs while retaining every category assignment.
 merged={}
 for row in rows:
  existing=merged.get(row['exhibitor_id'])
  if existing is None: merged[row['exhibitor_id']]=row
  else:
   if (existing['company_name'],existing['booth_no']) != (row['company_name'],row['booth_no']):raise ValueError('same source ID has conflicting fields')
   existing['category_ids'].extend(row['category_ids'])
 rows=list(merged.values())
 for row in rows: row['category_ids']='|'.join(row['category_ids'])
 ids=[r['exhibitor_id'] for r in rows]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate stable IDs')
 for n,r in enumerate(rows,1):r['source_position']=n
 for path,kind in ((Path(a.output),'csv'),(Path(a.json_output),'json')):
  path.parent.mkdir(parents=True,exist_ok=True)
  if kind=='csv':
   with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS,lineterminator='\n');w.writeheader();w.writerows(rows)
  else:path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'records':len(rows),'categories':len(CATEGORIES),'unique_ids':len(set(ids))}))
if __name__=='__main__':main()
