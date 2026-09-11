#!/usr/bin/env python3
"""Extract the public Taiwan Innotech Expo 2026 exhibitor list."""
from __future__ import annotations
import argparse,csv,html,json,re
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode,urljoin
from urllib.request import Request,urlopen
BASE='https://www.inventaipei.com.tw/en/exhibitor/company-name-data/index.html'
FIELDS=('exhibitor_id','application_id','company_name','brand_name','products','booth','detail_url','source_page','source_position')
def clean(value): return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',value or '')).split())
def page_url(page):return BASE+'?'+urlencode({'tags':'','pageSize':40,'currentPage':page})
def fetch(url):
 r=Request(url,headers={'User-Agent':'external-data-study-tie-extractor/1.0'})
 with urlopen(r,timeout=45) as x:return x.read().decode(x.headers.get_content_charset() or 'utf-8')
def field(block,label):
 m=re.search(r'<span>\s*'+re.escape(label)+r'.*?</span>\s*<p[^>]*>(.*?)</p>',block,re.S|re.I)
 return clean(m.group(1)) if m else ''
def parse_page(source,page):
 starts=list(re.finditer(r'<li id="([A-F0-9]{32})" class="[^"]*">',source))
 rows=[]
 for index,match in enumerate(starts):
  block=source[match.start():starts[index+1].start() if index+1<len(starts) else len(source)]
  name=re.search(r'<h3>.*?<a\s+href="([^"]+)"[^>]*>(.*?)</a>',block,re.S|re.I)
  app=re.search(r'name="applyId"\s+value="(\d+)"',block)
  if not name or not app or not clean(name.group(2)):raise ValueError('listing card missing name, URL, or application ID')
  booth=field(block,'Physical Show')
  rows.append({'exhibitor_id':match.group(1),'application_id':app.group(1),'company_name':clean(name.group(2)),'brand_name':field(block,'Brand Name：'),'products':field(block,'Products：'),'booth':booth,'detail_url':urljoin(BASE,name.group(1)),'source_page':page_url(page),'source_position':''})
 return rows
def advertised_total(source):
 counts=re.findall(r'href="/en/exhibitor/company-name-data/[A-Z]/list\.html"\s*>\s*[A-Z]\s*<span>\((\d+)\)</span>',source,re.S)
 if len(counts)!=26:raise ValueError('alphabetic exhibitor total is unavailable')
 return sum(map(int,counts))
def extract():
 first=fetch(page_url(1));total=advertised_total(first);rows=parse_page(first,1)
 if len(rows)!=40:raise ValueError('first page does not contain native page size 40')
 pages=(total+39)//40
 for page in range(2,pages+1):
  batch=parse_page(fetch(page_url(page)),page)
  expected=40 if page<pages else total-40*(pages-1)
  if len(batch)!=expected:raise ValueError(f'page {page} expected {expected}, got {len(batch)}')
  rows.extend(batch)
 if len(rows)!=total:raise ValueError(f'row count {len(rows)} != advertised {total}')
 if len({r['exhibitor_id'] for r in rows})!=total:raise ValueError('duplicate stable exhibitor IDs')
 if len({r['application_id'] for r in rows})!=total:raise ValueError('duplicate application IDs')
 for position,row in enumerate(rows,1):row['source_position']=str(position)
 return rows
def write(rows,csv_path,json_path):
 csv_path.parent.mkdir(parents=True,exist_ok=True);buf=__import__('io').StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(rows)
 for path,text,encoding in ((csv_path,buf.getvalue(),'utf-8-sig'),(json_path,json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf-8')):
  with NamedTemporaryFile('w',encoding=encoding,dir=path.parent,delete=False) as f:f.write(text);tmp=Path(f.name)
  tmp.replace(path)
 with csv_path.open(encoding='utf-8-sig',newline='') as f:assert list(csv.DictReader(f))==json.loads(json_path.read_text(encoding='utf-8'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--json-output',type=Path,required=True);a=p.parse_args();rows=extract();write(rows,a.output,a.json_output);print(json.dumps({'records':len(rows),'csv':str(a.output)}))
if __name__=='__main__':main()
