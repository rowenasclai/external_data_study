#!/usr/bin/env python3
"""Extract CMEF Autumn 2026 exhibitors from the organizer's public API."""
from __future__ import annotations
import argparse,csv,json,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request,urlopen
EID='e26c62a6-de1c-407b-979f-e1ea75211c22'; URL='https://api.cmef.com.cn/api/join/GetByExhibition?show=1&userId=null&modeType=-10'
FIELDS=['exhibitor_id','join_id','company_id','company_name','company_name_en','booth_code','hall','area','country','province','city','profile_url','source_url','source_position']
def fetch(page):
 p={'PageSize':10,'PageIndex':page,'ExhibitionId':EID,'Wheres':{'type':0,'wheres':{'WhereGroupOperator':1,'Predicates':[]}}}
 q=Request(URL,data=json.dumps(p).encode(),headers={'Content-Type':'application/json','User-Agent':'external-data-study/1.0'})
 last=None
 for attempt in range(1,6):
  try:
   with urlopen(q,timeout=60) as r:return json.load(r)
  except (TimeoutError,OSError,json.JSONDecodeError) as exc:
   last=exc
   if attempt<5: time.sleep(min(16,2**attempt))
 raise RuntimeError(f'page {page} failed after 5 attempts: {last}')
def main():
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--json-output',required=True);x=a.parse_args()
 first=fetch(1); total,pages=first['totalCount'],first['totalPages']
 # Two workers reduce transient 5xx responses while keeping the pass short.
 with ThreadPoolExecutor(max_workers=2) as pool:
  fetched={1:first,**{n:d for n,d in zip(range(2,pages+1),pool.map(fetch,range(2,pages+1)))}}
 all_items=[]
 for n in range(1,pages+1):
  data=fetched[n]
  if data['totalCount']!=total or data['totalPages']!=pages or data['pageIndex']!=n:raise ValueError(f'pagination metadata drift on page {n}')
  if n<pages and not data['items']:raise ValueError(f'empty interior page {n}')
  all_items.extend(data['items'])
 if len(all_items)!=total:raise ValueError(f'count mismatch {len(all_items)} != {total}')
 rows=[]
 for pos,i in enumerate(all_items,1):
  jid=str(i.get('joinId') or '');name=str(i.get('nameEn') or i.get('name') or '').strip()
  if not jid or not name or i.get('exhibitionId')!=EID:raise ValueError('missing identity/name or wrong edition')
  rows.append({'exhibitor_id':f'{EID}:{jid}','join_id':jid,'company_id':i.get('compId') or '','company_name':i.get('name') or '', 'company_name_en':i.get('nameEn') or '', 'booth_code':i.get('boothCode') or '', 'hall':i.get('exHall') or '', 'area':i.get('exArea') or '', 'country':i.get('country') or '', 'province':i.get('province') or '', 'city':i.get('city') or '', 'profile_url':f'https://i.cmef.com.cn/ex-detailsEn/{jid}?compId={i.get("compId") or ""}&exhibitionId={EID}', 'source_url':'https://i.cmef.com.cn/ex-listEn2','source_position':pos})
 if len({r['exhibitor_id'] for r in rows})!=len(rows):raise ValueError('duplicate stable IDs')
 for path,kind in ((Path(x.output),'csv'),(Path(x.json_output),'json')):
  path.parent.mkdir(parents=True,exist_ok=True)
  if kind=='csv':
   with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS,lineterminator='\n');w.writeheader();w.writerows(rows)
  else:path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'records':len(rows),'pages':pages,'unique_ids':len({r['exhibitor_id'] for r in rows})}))
if __name__=='__main__':main()
