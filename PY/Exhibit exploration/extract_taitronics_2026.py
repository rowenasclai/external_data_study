#!/usr/bin/env python3
"""Extract the public TAITRONICS & AIoT Taiwan 2026 company directory."""
from __future__ import annotations
import argparse,csv,html,json,re,time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
BASE='https://www.taitronics.tw/en/exhibitor/company-name-data/index.html'
FIELDS=['exhibitor_id','application_id','company_name','booth_no','show_area','profile_url','source_url','source_position']
def clean(s):return ' '.join(html.unescape(re.sub(r'<[^>]+>','',s)).split())
def get(page):
 u=BASE+'?'+urlencode({'currentPage':page,'pageSize':10})
 with urlopen(Request(u,headers={'User-Agent':'external-data-study/1.0'}),timeout=30) as r:return r.read().decode('utf-8','replace'),u
def parse(s,url):
 rows=[]
 for match in re.finditer(r'<li id="([^"]+)".*?(?=\n\s*<li id=|\n\s*</ul>\s*\n\s*</div>)',s,re.S):
  sid,body=match.group(1),match.group(0)
  m=re.search(r'<input[^>]+name="applyId"[^>]+value="([^"]+)".*?<a href="([^"]+)"[^>]*>(.*?)</a>',body,re.S)
  if not m:raise ValueError(f'unparseable source record {sid}')
  app,href,name=m.groups(); name=clean(name)
  booth=clean(re.search(r'Booth No\.:.*?<p>(.*?)</p>',body,re.S).group(1)) if re.search(r'Booth No\.:.*?<p>(.*?)</p>',body,re.S) else ''
  area=clean(re.search(r'Booth No\.:.*?<p>(.*?)<a ',body,re.S).group(1)) if re.search(r'Booth No\.:.*?<p>(.*?)<a ',body,re.S) else ''
  if not name or not app:raise ValueError('missing name/application ID')
  rows.append({'exhibitor_id':sid,'application_id':app,'company_name':name,'booth_no':booth,'show_area':area,'profile_url':'https://www.taitronics.tw'+href,'source_url':url})
 return rows
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--json-output',required=True);a=p.parse_args();rows=[]
 for page in range(1,27):
  s,u=get(page);rows.extend(parse(s,u));time.sleep(.1)
 if len(rows)!=252:raise ValueError(f'index count mismatch: {len(rows)} != 252')
 ids=[r['exhibitor_id'] for r in rows]
 if len(set(ids))!=len(ids):raise ValueError('duplicate stable IDs')
 for n,r in enumerate(rows,1):r['source_position']=n
 for path,kind in ((Path(a.output),'csv'),(Path(a.json_output),'json')):
  path.parent.mkdir(parents=True,exist_ok=True)
  if kind=='csv':
   with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS,lineterminator='\n');w.writeheader();w.writerows(rows)
  else:path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'records':len(rows),'unique_ids':len(set(ids))}))
if __name__=='__main__':main()
