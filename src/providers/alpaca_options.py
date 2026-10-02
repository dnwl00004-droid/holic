
from __future__ import annotations
import os, requests, math
from collections import defaultdict

BASE="https://data.alpaca.markets/v1beta1/options/snapshots/{symbol}"

def option_chain(symbol:str, feed="indicative"):
    key=os.getenv("APCA_API_KEY_ID");secret=os.getenv("APCA_API_SECRET_KEY")
    if not key or not secret:return {"enabled":False,"reason":"Alpaca credentials not set"}
    url=BASE.format(symbol=symbol.upper())
    headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret}
    params={"feed":feed,"limit":1000}
    out=[];token=None
    while True:
        if token:params["page_token"]=token
        r=requests.get(url,headers=headers,params=params,timeout=45);r.raise_for_status();data=r.json()
        snaps=data.get("snapshots",{})
        for contract,s in snaps.items():out.append({"contract":contract,**s})
        token=data.get("next_page_token")
        if not token:break
    return {"enabled":True,"feed":feed,"contracts":out}

def _parse_occ(sym):
    # Underlying padded variable + YYMMDD + C/P + 8 digit strike (x1000)
    import re
    m=re.match(r"^([A-Z.]+)(\d{6})([CP])(\d{8})$",sym)
    if not m:return None
    return {"underlying":m.group(1),"expiry":m.group(2),"type":m.group(3),"strike":int(m.group(4))/1000}

def option_positioning(chain:dict, spot:float|None=None):
    if not chain.get("enabled"):return chain
    rows=[]
    for x in chain["contracts"]:
        p=_parse_occ(x["contract"])
        if not p:continue
        g=x.get("greeks") or x.get("Greeks") or {}
        gamma=g.get("gamma")
        # Snapshot payload may not include OI. Keep calculations explicit if unavailable.
        oi=x.get("openInterest") or x.get("open_interest")
        if gamma is not None and oi is not None:
            exposure=float(gamma)*float(oi)*100*(spot or 1)**2/100
        else:exposure=None
        rows.append({**p,"gamma":gamma,"open_interest":oi,"gex_proxy":exposure})
    by=defaultdict(float)
    for r in rows:
        if r["gex_proxy"] is None:continue
        sign=1 if r["type"]=="C" else -1
        by[r["strike"]]+=sign*r["gex_proxy"]
    levels=sorted(by.items(),key=lambda z:abs(z[1]),reverse=True)[:10]
    return {"enabled":True,"feed":chain.get("feed"),"gex_by_strike":[{"strike":k,"gex_proxy":round(v,2)} for k,v in levels],
            "note":"GEX is shown only when the snapshot supplies open interest; otherwise unavailable."}
