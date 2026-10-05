#!/usr/bin/env python3
"""Extract the public All in Print China directory using its native 15-row pages."""
from __future__ import annotations
import argparse,csv,json,re,time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request,urlopen
from urllib.parse import urljoin
SOURCE_URL='https://www.allinprint.com/en/exhibitorList'
UA='external-data-study-all-in-print-extractor/1.0'
FIELDS=('exhibitor_id','company_name','country','detail_url','source_url','source_position')
TOTAL_RE=re.compile(r'Search results:\s*<span[^>]*>\s*(\d+)\s*</span>\s*in total',re.I)
CARD_RE=re.compile(r'<div class="exhibitorbox productres">(.*?)</div>\s*</div>\s*</div>',re.S)
ID_RE=re.compile(r'/en/exhibitorInfo\.html\?id=(\d+)')
NAME_RE=re.compile(r'<p class="compamyname[^>]*>\s*(.*?)\s*</p>',re.S)
COUNTRY_RE=re.compile(r'<p class="p2">\s*Regions/Country：\s*(.*?)\s*</p>',re.S)
def clean(s):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',s)).strip()
def fetch(page):
 u=f'{SOURCE_URL}?lang=en&page={page}';r=Request(u,headers={'User-Agent':UA,'Accept':'text/html'})
 with urlopen(r,timeout=45) as x:
  if x.status!=200:raise RuntimeError(f'page {page}: HTTP {x.status}')
  return x.read().decode(x.headers.get_content_charset() or 'utf-8'),u
def parse(t,u,require_total=False):
 total=TOTAL_RE.search(t)
 if require_total and not total:raise ValueError('missing reported total')
 rows=[]
 for card in CARD_RE.findall(t):
  i=ID_RE.search(card);n=NAME_RE.search(card);c=COUNTRY_RE.search(card)
  if not i or not n:raise ValueError('card missing stable ID or company name')
  rows.append({'exhibitor_id':i.group(1),'company_name':clean(n.group(1)),'country':clean(c.group(1)) if c else '', 'detail_url':urljoin(u,'/en/exhibitorInfo.html?id='+i.group(1)),'source_url':u,'source_position':''})
 if not rows:raise ValueError('page has zero cards')
 return rows,int(total.group(1)) if total else None
def write(rows,c,j):
 c.parent.mkdir(parents=True,exist_ok=True)
 for path,text,enc in [(c,None,'utf-8-sig'),(j,json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf-8')]:
  if text is None:
   import io;b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=FIELDS,lineterminator='\n');w.writeheader();w.writerows(rows);text=b.getvalue()
  with NamedTemporaryFile('w',encoding=enc,newline='',dir=path.parent,delete=False) as f:f.write(text);tmp=Path(f.name)
  tmp.replace(path)
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--json-output',type=Path,required=True);a=p.parse_args()
 t,u=fetch(1);rows,total=parse(t,u,True);pages=(total+len(rows)-1)//len(rows)
 for page in range(2,pages+1):
  time.sleep(.12);t,u=fetch(page);r,_=parse(t,u);rows.extend(r)
 if len(rows)!=total:raise ValueError(f'count mismatch: {len(rows)} != {total}')
 ids=[r['exhibitor_id'] for r in rows]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate stable IDs')
 for k,r in enumerate(rows,1):r['source_position']=str(k)
 write(rows,a.output,a.json_output)
 with a.output.open(encoding='utf-8-sig',newline='') as f:cr=list(csv.DictReader(f))
 jr=json.loads(a.json_output.read_text(encoding='utf-8'))
 if cr!=jr or len(jr)!=total:raise ValueError('artifact equivalence failed')
 print(f'total={total} pages={pages} csv={a.output} json={a.json_output}')
if __name__=='__main__':main()
