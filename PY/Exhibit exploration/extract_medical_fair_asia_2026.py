#!/usr/bin/env python3
"""Extract Medical Fair Asia 2026's public JetEngine exhibitor listing."""
from __future__ import annotations
import argparse,csv,html,json,re,time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request,urlopen
LANDING='https://www.medicalfair-asia.com/exhibitor-list/'
FIELDS=('exhibitor_id','company_name','country','booth_number','source_page','source_position')
def clean(v): return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',v)).split())
def form_pairs(key,value):
 if isinstance(value,dict):
  for k,v in value.items(): yield from form_pairs(f'{key}[{k}]',v)
 elif isinstance(value,list):
  for v in value: yield from form_pairs(f'{key}[]',v)
 elif value is None: yield key,''
 elif isinstance(value,bool): yield key,'true' if value else 'false'
 else: yield key,str(value)
def fetch_landing():
 r=Request(LANDING,headers={'User-Agent':'external-data-study-medical-fair-asia-extractor/1.0'})
 with urlopen(r,timeout=45) as x:return x.read().decode(x.headers.get_content_charset() or 'utf-8')
def config(payload):
 m=re.search(r'var JetSmartFilterSettings = (\{.*?\});',payload,re.S)
 if not m: raise ValueError('JetSmartFilterSettings missing')
 return json.loads(m.group(1))
def page(d,page):
 k,q='jet-engine','exhibitor-list';data=[]
 source={'action':'jet_smart_filters','provider':'jet-engine/exhibitor-list','paged':page,'query':{},'defaults':d['queries'][k][q],'settings':d['settings'][k][q],'props':d['props'][k][q]}
 for key,value in source.items():data.extend(form_pairs(key,value))
 r=Request(d['ajaxurl'],data=urlencode(data).encode(),headers={'Referer':LANDING,'User-Agent':'external-data-study-medical-fair-asia-extractor/1.0','Content-Type':'application/x-www-form-urlencoded'})
 with urlopen(r,timeout=45) as x:return json.loads(x.read().decode(x.headers.get_content_charset() or 'utf-8'))
def parse(fragment,source):
 rows=[]
 pat=r'jet-listing-grid__item[^>]*data-post-id="(\d+)"[^>]*>(.*?)(?=<div class="jet-listing-grid__item|\Z)'
 for ident,card in re.findall(pat,fragment,re.S):
  values=[clean(x) for x in re.findall(r'jet-listing-dynamic-field__content"\s*>(.*?)</div>',card,re.S)]
  if len(values)<3 or not values[0]:raise ValueError(f'listing card {ident} lacks expected fields')
  rows.append({'exhibitor_id':ident,'company_name':values[0],'country':values[1],'booth_number':values[2],'source_page':source,'source_position':''})
 return rows
def extract():
 d=config(fetch_landing()); first=page(d,1); meta=first['pagination'];total=int(meta['found_posts']);pages=int(meta['max_num_pages']);rows=parse(first['content'],LANDING)
 for n in range(2,pages+1):
  time.sleep(.25);result=page(d,n);p=result['pagination'];batch=parse(result['content'],LANDING+f'?page={n}')
  if int(p['found_posts'])!=total or int(p['page'])!=n or not batch or (n<pages and len(batch)!=50):raise ValueError(f'inconsistent source page {n}')
  rows.extend(batch)
 if len(rows)!=total:raise ValueError(f'row count {len(rows)} != {total}')
 ids=[r['exhibitor_id'] for r in rows]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate stable IDs')
 for n,row in enumerate(rows,1):row['source_position']=str(n)
 return rows
def write(rows,csv_path,json_path):
 csv_path.parent.mkdir(parents=True,exist_ok=True);s=__import__('io').StringIO(newline='');w=csv.DictWriter(s,fieldnames=FIELDS,lineterminator='\n');w.writeheader();w.writerows(rows)
 for path,content,encoding in ((csv_path,s.getvalue(),'utf-8-sig'),(json_path,json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf-8')):
  with NamedTemporaryFile('w',encoding=encoding,dir=path.parent,delete=False) as h:h.write(content);t=Path(h.name)
  t.replace(path)
 with csv_path.open(encoding='utf-8-sig',newline='') as h:assert list(csv.DictReader(h))==json.loads(json_path.read_text(encoding='utf-8'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--json-output',type=Path,required=True);a=p.parse_args();rows=extract();write(rows,a.output,a.json_output);print(json.dumps({'records':len(rows),'csv':str(a.output)}))
if __name__=='__main__':main()
