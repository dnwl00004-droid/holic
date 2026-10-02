from __future__ import annotations
from datetime import date, timedelta
import os, requests

BASE="https://api.finra.org/data/group/otcMarket/name/regShoDaily"
FIELDS=["tradeReportDate","securitiesInformationProcessorSymbolIdentifier","shortParQuantity","shortExemptParQuantity","totalParQuantity"]

def _normalize(row):
    get=lambda *ks: next((row.get(k) for k in ks if row.get(k) is not None),None)
    symbol=get("securitiesInformationProcessorSymbolIdentifier","symbolCode","issueSymbolIdentifier","symbol")
    total=get("totalParQuantity","totalVolume","totalParQty")
    short=get("shortParQuantity","shortVolume","shortParQty")
    short_ex=get("shortExemptParQuantity","shortExemptVolume","shortExemptParQty")
    trade_date=get("tradeReportDate","tradeDate","date")
    def num(v):
        try:return float(v)
        except:return None
    total,short,short_ex=num(total),num(short),num(short_ex)
    return {"symbol":symbol,"date":trade_date,"total_volume":total,"short_volume":short,
            "short_exempt_volume":short_ex,
            "short_volume_ratio_pct":round(short/total*100,2) if short is not None and total else None}

def _query_one_day(day:str, session=None, page_limit=5000):
    """FINRA production Query API, pinned to its partition field tradeReportDate."""
    url=os.getenv("FINRA_REGSHO_URL",BASE)
    s=session or requests.Session(); rows=[]; offset=0
    while True:
        payload={"limit":page_limit,"offset":offset,"fields":FIELDS,
                 "compareFilters":[{"compareType":"equal","fieldName":"tradeReportDate","fieldValue":day}]}
        r=s.post(url,json=payload,headers={"Accept":"application/json","Content-Type":"application/json"},timeout=45)
        if r.status_code==204:break
        r.raise_for_status(); page=r.json()
        if not isinstance(page,list): page=page.get("data",page.get("results",[]))
        rows.extend(page)
        total=int(r.headers.get("record-total",r.headers.get("Record-Total",len(rows))) or len(rows))
        offset += len(page)
        if not page or offset>=total or len(page)<page_limit:break
    return rows

def query_daily_short_volume(symbols:list[str], start_date:str, end_date:str, session=None, max_observations=20)->list[dict]:
    """Probe calendar dates backwards; filter requested symbols locally. Avoids ambiguous range/sort semantics."""
    wanted={x.upper() for x in symbols}; start=date.fromisoformat(start_date); end=date.fromisoformat(end_date)
    s=session or requests.Session(); out=[]; observed=0; d=end
    while d>=start and observed<max_observations:
        raw=_query_one_day(d.isoformat(),session=s)
        if raw:
            observed += 1
            for row in raw:
                n=_normalize(row)
                if not wanted or (n.get("symbol") or "").upper() in wanted:out.append(n)
        d-=timedelta(days=1)
    return out

def summarize_short_volume(rows:list[dict])->dict[str,dict]:
    by={}
    for r in rows:
        if not r.get("symbol"):continue
        by.setdefault(r["symbol"],[]).append(r)
    out={}
    for t,arr in by.items():
        # Multiple reporting facilities can produce multiple rows for one symbol/day; aggregate first.
        days={}
        for x in arr:
            z=days.setdefault(str(x.get("date")),{"short":0.0,"total":0.0})
            z["short"] += x.get("short_volume") or 0; z["total"] += x.get("total_volume") or 0
        ratios=[]
        for day,z in sorted(days.items()):
            if z["total"]>0:ratios.append((day,round(z["short"]/z["total"]*100,2)))
        vals=[v for _,v in ratios];latest=vals[-1] if vals else None
        avg5=round(sum(vals[-5:])/len(vals[-5:]),2) if vals else None
        avg20=round(sum(vals[-20:])/len(vals[-20:]),2) if vals else None
        out[t]={"latest_ratio_pct":latest,"avg5_ratio_pct":avg5,"avg20_ratio_pct":avg20,
                "trend":"UP" if latest is not None and avg20 is not None and latest>avg20+3 else
                        "DOWN" if latest is not None and avg20 is not None and latest<avg20-3 else "FLAT",
                "observations":len(vals),"source":"FINRA Reg SHO daily short sale volume",
                "caveat":"Off-exchange short-sale volume is not short interest."}
    return out
