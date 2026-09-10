#!/usr/bin/env python3
"""Extract the public Tech Week Singapore 2026 exhibitor directory."""
from __future__ import annotations
import argparse,csv,html,json,re,time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode,urljoin
from urllib.request import Request,urlopen
BASE='https://www.singaporetechnologyweek.com/exhibitor-list-2026'
GROUP='2C6C5EE9-exhibitors'
FIELDS=('exhibitor_id','company_name','stand','sponsor_status','profile_url','logo_url','source_page','source_position')
def clean(v:str)->str:return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',v)).split())
def fetch(page:int)->str:
 u=BASE+'?'+urlencode({'searchgroup':GROUP,'page':page}); r=Request(u,headers={'User-Agent':'external-data-study-tech-week-extractor/1.0'});
 with urlopen(r,timeout=40) as x:return x.read().decode(x.headers.get_content_charset() or 'utf-8')
def parse(payload:str,source:str)->tuple[list[dict[str,str]],int]:
 total=re.search(r'data-totalcount="(\d+)"',payload)
 if not total:raise ValueError('Tech Week published total missing')
 rows=[]
 pattern=r'<li class="[^"]*js-library-item[^"]*"(?P<attrs>[^>]*)>(?P<body>.*?)</li>'
 for m in re.finditer(pattern,payload,re.S):
  attrs,body=m.group('attrs'),m.group('body'); ident=re.search(r'data-content-i-d="(\d+)"',attrs); href=re.search(r'data-href="([^"]+)"',attrs); name=re.search(r'<h2[^>]*>(.*?)</h2>',body,re.S); logo=re.search(r'<img src="([^"]+)"',body); stand=re.search(r'Stand:\s*([^<\n]+)',body); status=re.search(r'header__status__item[^>]*>(.*?)</span>',body,re.S)
  if not ident or not name:raise ValueError('Tech Week card missing stable ID or name')
  rows.append({'exhibitor_id':ident.group(1),'company_name':clean(name.group(1)),'stand':clean(stand.group(1)) if stand else '','sponsor_status':clean(status.group(1)) if status else '','profile_url':urljoin(BASE,href.group(1)) if href else '','logo_url':html.unescape(logo.group(1)) if logo else '','source_page':source,'source_position':''})
 return rows,int(total.group(1))
def extract()->list[dict[str,str]]:
 first_url=BASE+'?'+urlencode({'searchgroup':GROUP,'page':1}); first,total=parse(fetch(1),first_url); pages=(total+49)//50; rows=first
 for page in range(2,pages+1):
  time.sleep(.2); url=BASE+'?'+urlencode({'searchgroup':GROUP,'page':page}); batch,seen=parse(fetch(page),url)
  if seen!=total or not batch or (page<pages and len(batch)!=50):raise ValueError(f'Tech Week inconsistent page {page}')
  rows.extend(batch)
 if len(rows)!=total:raise ValueError(f'Tech Week count {len(rows)} != {total}')
 ids=[r['exhibitor_id'] for r in rows]
 if len(ids)!=len(set(ids)):raise ValueError('Tech Week duplicate stable IDs')
 for i,row in enumerate(rows,1):row['source_position']=str(i)
 return rows
def write(rows:list[dict[str,str]],csv_path:Path,json_path:Path)->None:
 csv_path.parent.mkdir(parents=True,exist_ok=True); b=__import__('io').StringIO(newline=''); w=csv.DictWriter(b,fieldnames=FIELDS,lineterminator='\n');w.writeheader();w.writerows(rows)
 for p,c,e in ((csv_path,b.getvalue(),'utf-8-sig'),(json_path,json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf-8')):
  with NamedTemporaryFile('w',encoding=e,dir=p.parent,delete=False) as h:h.write(c);t=Path(h.name)
  t.replace(p)
 with csv_path.open(encoding='utf-8-sig',newline='') as h:assert list(csv.DictReader(h))==json.loads(json_path.read_text(encoding='utf-8'))
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--json-output',type=Path,required=True);a=p.parse_args();rows=extract();write(rows,a.output,a.json_output);print(json.dumps({'records':len(rows),'csv':str(a.output)}));return 0
if __name__=='__main__':raise SystemExit(main())
