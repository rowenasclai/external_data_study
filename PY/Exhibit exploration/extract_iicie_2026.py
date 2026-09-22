#!/usr/bin/env python3
"""Extract the public IICIE 2026 exhibitor directory."""
from __future__ import annotations
import argparse, csv, html, json, re, time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

LANDING = 'https://exhibitors.iicieexpo.com/gwen/index.html'
ENDPOINT = 'https://exhibitors.iicieexpo.com/gwen/data/zslist.ashx?method=dg_zhanshang&random=1'
FIELDS = ('exhibitor_id','company_name','exhibition_area','hall','booth_number','main_products','profile_url','logo_url','company_profile','source_page','source_position')

def clean(value: str) -> str:
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', value)).split())

def value(card: str, label: str) -> str:
    match = re.search(r'<dt>\s*' + re.escape(label) + r'\s*</dt>\s*<dd>(.*?)</dd>', card, re.S)
    return clean(match.group(1)) if match else ''

def parse_page(payload: str, source_page: str) -> tuple[list[dict[str,str]], int]:
    parts = payload.split('!@#$%^&*', 1)
    if len(parts) != 2: raise ValueError('IICIE response separator missing')
    cards, pager = parts
    total_match = re.search(r'Total\s*:\s*(\d+)', pager, re.I)
    if not total_match: raise ValueError('IICIE total missing')
    rows=[]
    for card in re.findall(r'<li>(.*?)</li>', cards, re.S):
        identity = re.search(r"win_zx\('(\d+)'\)", card)
        name = re.search(r'<h3 class="title">(.*?)</h3>', card, re.S)
        profile = re.search(r'href="([^"]*zsen\d+\.html)"', card)
        logo = re.search(r'<img src="([^"]+)"', card)
        if not identity or not name: raise ValueError('IICIE card missing stable ID or company name')
        rows.append({'exhibitor_id':identity.group(1),'company_name':clean(name.group(1)),'exhibition_area':value(card,'Exhibition Area：'),'hall':value(card,'Hall：'),'booth_number':value(card,'Booth No：'),'main_products':value(card,'Main products：'),'profile_url':urljoin(LANDING,profile.group(1)) if profile else '','logo_url':urljoin(LANDING,logo.group(1)) if logo else '','company_profile':'','source_page':source_page,'source_position':''})
    return rows, int(total_match.group(1))

def fetch(page: int) -> tuple[list[dict[str,str]],int]:
    data=urlencode({'pageindex':page,'pagesize':12,'zq':'','zg':'','zsqy':'','zslx':'','cxtj':'','zpfw':''}).encode()
    request=Request(ENDPOINT,data=data,headers={'User-Agent':'external-data-study-iicie-extractor/1.0','Referer':LANDING})
    with urlopen(request,timeout=40) as response: payload=response.read().decode(response.headers.get_content_charset() or 'utf-8')
    return parse_page(payload, ENDPOINT + '&pageindex=' + str(page))

def extract() -> list[dict[str,str]]:
    first,total=fetch(1); pages=(total+11)//12; rows=first
    for page in range(2,pages+1):
        time.sleep(.2); batch,observed=fetch(page)
        if observed != total or (page < pages and len(batch)!=12) or not batch: raise ValueError(f'IICIE inconsistent page {page}')
        rows.extend(batch)
    if len(rows)!=total: raise ValueError(f'IICIE count {len(rows)} != {total}')
    ids=[r['exhibitor_id'] for r in rows]
    if len(ids)!=len(set(ids)): raise ValueError('IICIE duplicate stable IDs')
    for i,row in enumerate(rows,1): row['source_position']=str(i)
    return rows

def write(rows:list[dict[str,str]],csv_path:Path,json_path:Path)->None:
    csv_path.parent.mkdir(parents=True,exist_ok=True)
    text=__import__('io').StringIO(newline=''); writer=csv.DictWriter(text,fieldnames=FIELDS,lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    for path,content,encoding in ((csv_path,text.getvalue(),'utf-8-sig'),(json_path,json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf-8')):
        with NamedTemporaryFile('w',encoding=encoding,dir=path.parent,delete=False) as handle: handle.write(content); temporary=Path(handle.name)
        temporary.replace(path)
    with csv_path.open(encoding='utf-8-sig',newline='') as handle: assert list(csv.DictReader(handle))==json.loads(json_path.read_text(encoding='utf-8'))

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--json-output',type=Path,required=True); args=parser.parse_args(); rows=extract(); write(rows,args.output,args.json_output); print(json.dumps({'records':len(rows),'csv':str(args.output)})); return 0
if __name__=='__main__': raise SystemExit(main())
