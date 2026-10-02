from __future__ import annotations
import json, sys
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.reliability import validate_snapshot,valid_history,is_demo

class AuditHTML(HTMLParser):
    def __init__(self):super().__init__();self.ids=set();self.duplicates=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):
            if a['id'] in self.ids:self.duplicates.append(a['id'])
            self.ids.add(a['id'])
        if tag in ('script','link') and (a.get('src') or a.get('href')):self.links.append(a.get('src') or a.get('href'))

def validate(root=ROOT/'web'):
    root=Path(root);html=AuditHTML();html.feed((root/'index.html').read_text())
    if html.duplicates:raise ValueError('Duplicate IDs: '+str(html.duplicates))
    for link in html.links:
        if ':' not in link and not (root/link).exists():raise ValueError('Missing asset '+link)
    s=json.loads((root/'latest.json').read_text());validate_snapshot(s)
    manifest=json.loads((root/'history/index.json').read_text());observations=0;seen=set()
    for item in manifest['items']:
        if item['id'] in seen: raise ValueError('Duplicate history ID '+item['id'])
        seen.add(item['id'])
        if not item.get('path'):continue
        path=root/item['path']
        if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe history path')
        d=json.loads(path.read_text())
        if is_demo(d) or not valid_history(d.get('history')):raise ValueError('Invalid history '+item['id'])
        if len(d['history'])!=item['count']:raise ValueError('Manifest count mismatch '+item['id'])
        observations+=item['count']
    # Production publishing rejects even unused illustrative payloads.
    for path in root.rglob('*.json'):
        d=json.loads(path.read_text())
        if is_demo(d):raise ValueError('Illustrative payload in production web root '+str(path))
    return {'html_ids':len(html.ids),'stocks':len(s['tickers']),'history_series':sum(bool(x.get('path')) for x in manifest['items']),'observations':observations,'duplicate_ids':0}

if __name__=='__main__':
    print(json.dumps(validate()))
