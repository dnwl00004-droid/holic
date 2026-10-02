from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import re, requests
from lxml import html
from ..reliability import store_history

SERIES={
 "WCESTUS1":("Crude Inventory ex-SPR","thousand bbl"),
 "WCSSTUS1":("Strategic Petroleum Reserve","thousand bbl"),
 "WGTSTUS1":("Gasoline Inventory","thousand bbl"),
 "WDISTUS1":("Distillate Inventory","thousand bbl"),
 "WCRFPUS2":("US Crude Production","thousand bbl/day"),
 "WPULEUS3":("Refinery Utilization","%"),
 "WCRIMUS2":("Crude Imports","thousand bbl/day"),
 "WCREXUS2":("Crude Exports","thousand bbl/day"),
}

def parse_history(text):
    tree=html.fromstring(text);values={}
    for row in tree.xpath('//tr'):
        cells=[" ".join(c.xpath('.//text()')).strip() for c in row.xpath('./td')]
        if not cells or not re.fullmatch(r"\d{4}-[A-Za-z]{3}",cells[0]):continue
        year=int(cells[0][:4])
        for i in range(1,len(cells)-1,2):
            if not re.fullmatch(r"\d{2}/\d{2}",cells[i]):continue
            try:
                dt=datetime.strptime(str(year)+"/"+cells[i],"%Y/%m/%d").date().isoformat();value=float(cells[i+1].replace(",",""));values[dt]={"date":dt,"value":value}
            except ValueError:continue
    return sorted(values.values(),key=lambda r:r['date'])

def build_eia(root):
    root=Path(root)
    def fetch(item):
        sid,(label,unit)=item;url=f"https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=W&n=PET&s={sid}";path=root/'eia'/(sid+'.json');meta={"label":label,"unit":unit,"category":"eia","transform":"level"}
        try:
            r=requests.get(url,timeout=30);r.raise_for_status();h=parse_history(r.text)
            d=store_history(path,{"id":sid,"kind":"eia","source":"U.S. EIA","source_url":url,"meta":meta,"history":h,"method":"published weekly observations"})
        except Exception as e:d=store_history(path,None,type(e).__name__)
        h=d['history']
        return {"id":sid,"kind":"eia",**meta,"path":'history/eia/'+sid+'.json' if h else None,"count":len(h),"start":h[0]['date'] if h else None,"end":h[-1]['date'] if h else None,"source":"U.S. EIA","status":d['status'],"last_attempt":d.get('last_attempt'),"last_success":d.get('last_success'),"error":d.get('error'),"refresh_frequency":"weekly","method":"published weekly observations"}
    with ThreadPoolExecutor(max_workers=4) as pool:return list(pool.map(fetch,SERIES.items()))
