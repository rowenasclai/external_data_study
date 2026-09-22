#!/usr/bin/env python3
"""Extract Mining Indonesia 2026's public MINING365 exhibitor API."""
from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request,urlopen
BASE='https://exhibitors.informamarkets-info.com'; LANDING=BASE+'/event/MIN2026'
FIELDS=('exhibitor_id','company_name','country','stand_number','address','profile_description','product_categories','logo_url','profile_url','source_position')
def clean(v):return ' '.join(re.sub(r'<[^>]+>',' ',str(v or '')).split())
def payload():return {'fn':'getExhibitor','orderfields':'["FeaturedExhibitor","ExhibitorNameEn","StandNoStr","CountryEn"]','filter[country]':'','filter[companyprefix]':'','filter[productcategory]':'','filter[hashtags]':'','filter[businessnature]':'','filter[exhibitortype]':'','filter[venue]':'','filter[fairlocation]':'','HideEmptyProducts':'0','filter[new]':'','filter[sustainable]':'','filter[besustainable]':'','order[0][column]':'0','order[0][dir]':'desc','order[1][column]':'1','order[1][dir]':'asc','start':'0','length':'10000','draw':'1','dt':'1','SearchLog':'1','FairID':'uDzPDvC6SAeF17cQndacaA==','FairCode':'34jRr4CQy7DyeOQZgsAvfw==','DefineCountry':'False','UseOldCountry':'False','MyList':'0','Email':'','Url':LANDING}
def extract():
 r=Request(BASE+'/api?'+urlencode(payload()),headers={'User-Agent':'external-data-study-mining-indonesia-extractor/1.0','Referer':LANDING})
 with urlopen(r,timeout=45) as x:data=json.loads(x.read())
 total=int(data['recordsTotal']);items=data['data']
 if len(items)!=total:raise ValueError(f'API returned {len(items)} of {total}')
 rows=[]
 for pos,item in enumerate(items,1):
  ident=str(item.get('ExhibitorID','')).strip();name=clean(item.get('ExhibitorNameEn'))
  if not ident or not name:raise ValueError('missing stable ID or company name')
  slug=re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')
  rows.append({'exhibitor_id':ident,'company_name':name,'country':clean(item.get('CountryEn')),'stand_number':clean(item.get('StandNoStr')),'address':clean(item.get('Field01')),'profile_description':clean(item.get('DescEn')),'product_categories':clean(item.get('ProductCategoryEn')),'logo_url':str(item.get('PhotoURL') or ''),'profile_url':f'{LANDING}/en-US/exhibitor/{ident}/{slug}','source_position':str(pos)})
 if len({r['exhibitor_id'] for r in rows})!=total:raise ValueError('duplicate stable IDs')
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
