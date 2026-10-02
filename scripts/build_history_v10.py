from __future__ import annotations
import argparse,json
from pathlib import Path
import requests
from src.providers.history_v10 import build_fred_history,build_commodity_history,build_eia_history,build_market_history,build_calendar_archive


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--snapshot',default='web/latest.json')
    ap.add_argument('--history-root',default='web/history')
    ap.add_argument('--calendar-start-year',type=int,default=2019)
    a=ap.parse_args()
    root=Path(a.history_root);root.mkdir(parents=True,exist_ok=True)
    session=requests.Session()
    fred=build_fred_history(root/'fred',session=session)
    commodities=build_commodity_history(root/'commodities')
    eia=build_eia_history(root/'eia')
    market=build_market_history(root/'market')
    cal=build_calendar_archive(a.calendar_start_year)
    (root/'calendar_archive.json').write_text(json.dumps(cal,separators=(',',':')),encoding='utf-8')
    items=fred+commodities+eia+market
    index={
        'schema_version':'10.0',
        'items':items,
        'calendar_path':'history/calendar_archive.json',
        'counts':{
            'fred':sum(x.get('kind')=='fred' and x.get('count',0)>0 for x in items),
            'commodities':sum(x.get('kind') in {'commodity','derived'} and x.get('count',0)>0 for x in items),
            'eia':sum(x.get('kind')=='eia' and x.get('count',0)>0 for x in items),
            'market':sum(x.get('kind')=='market' and x.get('count',0)>0 for x in items),
            'calendar_events':len(cal.get('events',[])),
        },
        'notes':[
            'Each series is stored separately so MAX-range charts do not bloat latest.json.',
            'FRED files contain transformed display history and raw values where applicable.',
            'Futures history can be affected by contract rolls.',
            'Historical event archive is source-dependent and does not include consensus forecasts unless a separate provider is added.'
        ]
    }
    (root/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')

    sp=Path(a.snapshot)
    if sp.exists():
        snap=json.loads(sp.read_text(encoding='utf-8'))
        snap.setdefault('meta',{})['schema_version']='10.0'
        snap['history_v10']={'index_path':'history/index.json','calendar_path':'history/calendar_archive.json','counts':index['counts']}
        snap.setdefault('sources',{})['history_v10']={
            'macro':'FRED full available series history',
            'commodities':'Yahoo Finance futures max available history',
            'energy_inventories':'U.S. EIA weekly historical tables',
            'calendar':'BLS/FOMC historical schedule archive plus current BEA schedule',
        }
        sp.write_text(json.dumps(snap,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps(index['counts']))

if __name__=='__main__':main()
