#!/usr/bin/env python3
"""Build the GitHub Pages event-to-customer-list dashboard from the control-sheet snapshot."""
from __future__ import annotations
import csv, html, json
from pathlib import Path

SNAPSHOT=Path('Result/Exhibition Organizers/control_sheet_snapshot.csv')
OUTPUT=Path('index.html')
OVERRIDES={
 'Taiwan Innotech Expo 2026 (TIE 2026)':'Result/Exhibition Organizers/Taiwan Innotech Expo/taiwan_innotech_expo_2026_exhibitors.csv',
}
def rows():
 with SNAPSHOT.open(encoding='utf-8-sig',newline='') as f: raw=list(csv.reader(f))
 header_index=next(i for i,row in enumerate(raw) if {'Event Name','Status','Extracted File Name'}<=set(row))
 header=raw[header_index];out=[]
 for row in raw[header_index+1:]:
  if len(row)<len(header):row += ['']*(len(header)-len(row))
  item=dict(zip(header,row))
  if item.get('Event Name','').strip():out.append(item)
 return out
def artifact_paths():
 result={}
 for path in Path('Result/Exhibition Organizers').rglob('*.csv'):
  if path.name=='control_sheet_snapshot.csv':continue
  result.setdefault(path.name,path.as_posix())
 return result
def main():
 events=rows();paths=artifact_paths()
 payload=[]
 for event in events:
  filename=event.get('Extracted File Name','').strip()
  link=paths.get(filename) if filename else OVERRIDES.get(event['Event Name'])
  payload.append({'name':event['Event Name'],'organizer':event.get('Event Organizer',''),'dates':event.get('Event Dates',''),'location':event.get('Location',''),'status':event.get('Status',''),'eventUrl':event.get('Event URL',''),'directoryUrl':event.get('Exhibitor Directory Link',''),'customerList':link})
 data=json.dumps(payload,ensure_ascii=False).replace('</','<\\/')
 OUTPUT.write_text(TEMPLATE.replace('__DATA__',data),encoding='utf-8')
 print(f'events={len(payload)} customer_lists={sum(bool(x["customerList"]) for x in payload)} output={OUTPUT}')
TEMPLATE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exhibition Customer Lists</title><style>
:root{font-family:Inter,system-ui,sans-serif;color:#172033;background:#f5f7fb}body{margin:0}.wrap{max-width:1280px;margin:auto;padding:38px 24px}h1{margin:0;font-size:clamp(1.7rem,4vw,2.5rem)}.sub{color:#536075;margin:10px 0 28px}.bar{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:18px}.stat{background:#fff;border:1px solid #dfe5ef;border-radius:10px;padding:13px 18px;font-weight:600}.search{margin-left:auto;min-width:280px;padding:12px;border:1px solid #aeb9cb;border-radius:8px;font:inherit}.tablewrap{background:#fff;border:1px solid #dfe5ef;border-radius:12px;overflow:auto}table{width:100%;border-collapse:collapse;min-width:900px}th,td{padding:14px 16px;border-bottom:1px solid #e7ebf2;text-align:left;vertical-align:top}th{background:#f0f4fa;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:#536075}td{font-size:.92rem}.event{font-weight:700}.muted{color:#657085}.badge{display:inline-block;max-width:230px;padding:4px 8px;border-radius:99px;background:#edf2f8;color:#32425a;font-size:.78rem}.list{display:inline-block;background:#0759c7;color:#fff;padding:8px 11px;border-radius:7px;text-decoration:none;font-weight:700;white-space:nowrap}.list:hover{background:#0349a5}.na{color:#7d8795;font-size:.82rem}a.external{color:#0759c7;text-decoration:none;font-size:.82rem}a.external:hover{text-decoration:underline}@media(max-width:700px){.wrap{padding:26px 14px}.search{margin-left:0;width:100%}}
</style><body><main class="wrap"><h1>Exhibition customer lists</h1><p class="sub">Select an event to download its published exhibitor/customer list. The table is generated from the public control-sheet snapshot.</p><section class="bar"><div class="stat" id="events"></div><div class="stat" id="lists"></div><input class="search" id="search" placeholder="Search event, location, organizer…" aria-label="Search events"></section><div class="tablewrap"><table><thead><tr><th>Event</th><th>Dates & location</th><th>Organizer</th><th>Status</th><th>Customer list</th></tr></thead><tbody id="body"></tbody></table></div></main><script>const events=__DATA__;const body=document.querySelector('#body');const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function draw(){const q=document.querySelector('#search').value.toLowerCase();const filtered=events.filter(e=>Object.values(e).join(' ').toLowerCase().includes(q));body.innerHTML=filtered.map(e=>`<tr><td><div class="event">${esc(e.name)}</div>${e.eventUrl?`<a class="external" target="_blank" rel="noopener" href="${esc(e.eventUrl)}">Official event ↗</a>`:''}</td><td>${esc(e.dates)}<br><span class="muted">${esc(e.location)}</span></td><td>${esc(e.organizer)}</td><td><span class="badge">${esc(e.status||'Not set')}</span></td><td>${e.customerList?`<a class="list" href="${encodeURI(e.customerList)}" download>Download CSV</a>`:'<span class="na">No published list</span>'}</td></tr>`).join('')||'<tr><td colspan="5">No matching events.</td></tr>'}document.querySelector('#events').textContent=`${events.length} events`;document.querySelector('#lists').textContent=`${events.filter(e=>e.customerList).length} published customer lists`;document.querySelector('#search').addEventListener('input',draw);draw();</script></body></html>'''
if __name__=='__main__':main()
