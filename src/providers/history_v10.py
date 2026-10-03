from __future__ import annotations
from io import StringIO
from pathlib import Path
from datetime import date, datetime
import json, math, re
import requests
import pandas as pd

from .macro_official_v8 import FRED_CSV, HEADERS, SERIES as BASE_SERIES
from .calendar_v9 import bls_events, fomc_events, bea_events

# Additional series that are valuable in historical macro work but were not needed
# for the compact current-state regime score.
EXTRA_FRED_SERIES = {
    "A191RL1Q225SBEA":{"label":"Real GDP QoQ SAAR","category":"growth","unit":"%","transform":"level"},
    "JTSJOL":{"label":"JOLTS Job Openings","category":"growth","unit":"thousand","transform":"level"},
    "ICSA":{"label":"Initial Jobless Claims","category":"growth","unit":"claims","transform":"level"},
    "CES0500000003":{"label":"Average Hourly Earnings YoY","category":"inflation","unit":"%","transform":"yoy"},
    "WPSFD4":{"label":"PPI Final Demand YoY","category":"inflation","unit":"%","transform":"yoy"},
    "UMCSENT":{"label":"Michigan Consumer Sentiment","category":"growth","unit":"index","transform":"level"},
    "NFCI":{"label":"Chicago Fed NFCI","category":"financial_conditions","unit":"index","transform":"level"},
    "SOFR":{"label":"SOFR","category":"rates","unit":"%","transform":"level"},
    "EFFR":{"label":"Effective Federal Funds Rate (NY Fed)","category":"rates","unit":"%","transform":"level"},
    "DGS3MO":{"label":"US Treasury 3M","category":"rates","unit":"%","transform":"level"},
    "DGS5":{"label":"US Treasury 5Y","category":"rates","unit":"%","transform":"level"},
    "DFII5":{"label":"5Y Real Yield","category":"rates","unit":"%","transform":"level"},
    "T5YIE":{"label":"5Y Breakeven Inflation","category":"inflation","unit":"%","transform":"level"},
    "AAA10Y":{"label":"Aaa Corporate - 10Y Treasury Spread","category":"credit","unit":"%","transform":"level"},
    "BAA10Y":{"label":"Baa Corporate - 10Y Treasury Spread","category":"credit","unit":"%","transform":"level"},
    "STLFSI4":{"label":"St. Louis Fed Financial Stress Index","category":"financial_conditions","unit":"index","transform":"level"},
    "U6RATE":{"label":"U-6 Underemployment Rate","category":"growth","unit":"%","transform":"level"},
    "CIVPART":{"label":"Labor Force Participation Rate","category":"growth","unit":"%","transform":"level"},
    "PERMIT":{"label":"Building Permits","category":"housing","unit":"thousand SAAR","transform":"level"},
    "MORTGAGE30US":{"label":"30Y Fixed Mortgage Rate","category":"housing","unit":"%","transform":"level"},
    "DEXKOUS":{"label":"KRW per USD","category":"fx","unit":"KRW/USD","transform":"level"},
    "DCOILWTICO":{"label":"WTI Spot Price","category":"energy_spot","unit":"$/bbl","transform":"level"},
    "DCOILBRENTEU":{"label":"Brent Spot Price","category":"energy_spot","unit":"$/bbl","transform":"level"},
    "DHHNGSP":{"label":"Henry Hub Natural Gas Spot","category":"energy_spot","unit":"$/MMBtu","transform":"level"},
}
FRED_SERIES = {**BASE_SERIES, **EXTRA_FRED_SERIES}


def _fred_full_rows(series:str, session=None) -> list[dict]:
    s=session or requests.Session()
    # Retry one transport interruption, never an access denial or rate limit.
    for attempt in range(2):
        try:
            r=s.get(FRED_CSV.format(series=series), headers=HEADERS, timeout=(8,30 if attempt==0 else 12))
            r.raise_for_status()
            break
        except (requests.Timeout,requests.ConnectionError):
            if attempt: raise
        except requests.HTTPError:
            if attempt or r.status_code not in (502,503,504): raise
    r.raise_for_status()
    df=pd.read_csv(StringIO(r.text))
    if series not in df.columns: raise ValueError("unexpected_FRED_series")
    dc=df.columns[0]; vc=series
    df[dc]=pd.to_datetime(df[dc],errors="coerce")
    df[vc]=pd.to_numeric(df[vc].replace(".",None),errors="coerce")
    df=df.dropna().sort_values(dc)
    return [{"date":d.strftime("%Y-%m-%d"),"value":float(v)} for d,v in zip(df[dc],df[vc])]


def _nearest_value(idx:pd.DatetimeIndex, vals:pd.Series, target:pd.Timestamp, tolerance_days=50):
    if len(idx)==0:return None
    pos=idx.get_indexer([target],method="nearest",tolerance=pd.Timedelta(days=tolerance_days))[0]
    if pos<0:return None
    try:return float(vals.iloc[pos])
    except Exception:return None


def transform_history(rows:list[dict], transform:str) -> list[dict]:
    if not rows:return []
    df=pd.DataFrame(rows)
    df["date"]=pd.to_datetime(df["date"]);df=df.sort_values("date").drop_duplicates("date",keep="last")
    idx=pd.DatetimeIndex(df["date"]);vals=df["value"].astype(float)
    baseline=None
    if transform in ("yoy","diff3"):
        targets=idx-pd.DateOffset(years=1) if transform=="yoy" else idx-pd.DateOffset(months=3)
        baseline=idx.get_indexer(targets,method="nearest",tolerance=pd.Timedelta(days=50))
    out=[]
    for i,(dt,val) in enumerate(zip(idx,vals)):
        display=None
        if transform=="level":display=val
        elif transform=="millions_to_bn":display=val/1000.0
        elif transform=="yoy":
            pos=baseline[i];prev=float(vals.iloc[pos]) if 0<=pos<i else None
            if prev not in (None,0):display=(val/prev-1)*100
        elif transform=="diff3":
            pos=baseline[i];prev=float(vals.iloc[pos]) if 0<=pos<i else None
            if prev is not None:display=val-prev
        else:display=val
        if display is not None and math.isfinite(float(display)):
            out.append({"date":dt.strftime("%Y-%m-%d"),"value":round(float(display),6),"raw":round(float(val),6)})
    return out


def build_fred_history(output_dir:str|Path, session=None):
    outdir=Path(output_dir);outdir.mkdir(parents=True,exist_ok=True)
    manifest=[];s=session or requests.Session()
    for sid,meta in FRED_SERIES.items():
        try:
            raw=_fred_full_rows(sid,s)
            hist=transform_history(raw,meta.get("transform","level"))
            payload={"id":sid,"kind":"fred","source":"FRED","meta":meta,"history":hist,
                     "raw_observation_count":len(raw)}
            (outdir/f"{sid}.json").write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
            if hist:
                manifest.append({"id":sid,"kind":"fred","label":meta["label"],"category":meta["category"],"unit":meta["unit"],
                                 "path":f"history/fred/{sid}.json","start":hist[0]["date"],"end":hist[-1]["date"],"count":len(hist),"source":"FRED"})
        except Exception as e:
            manifest.append({"id":sid,"kind":"fred","label":meta["label"],"category":meta["category"],"unit":meta["unit"],
                             "path":None,"count":0,"error":type(e).__name__,"source":"FRED"})
    return manifest


def build_commodity_history(output_dir:str|Path):
    import yfinance as yf
    from .commodities_v9 import COMMODITIES
    outdir=Path(output_dir);outdir.mkdir(parents=True,exist_ok=True)
    tickers=list(COMMODITIES)
    raw=yf.download(tickers,period="max",interval="1d",auto_adjust=True,repair=True,group_by="ticker",threads=True,progress=False)
    manifest=[];series={}
    for t,meta in COMMODITIES.items():
        try:
            d=raw[t].dropna(how="all")
            c=(d["Close"] if "Close" in d.columns else d["close"]).dropna()
            hist=[{"date":str(i.date()),"value":round(float(v),6)} for i,v in c.items()]
            if not hist:continue
            payload={"id":t,"kind":"commodity","source":"Yahoo Finance via yfinance","meta":meta,"history":hist,
                     "caveat":"Continuous/front-month futures history can be affected by contract rolls."}
            safe=t.replace("=","_").replace("^","_")
            path=f"history/commodities/{safe}.json"
            (outdir/f"{safe}.json").write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
            manifest.append({"id":t,"kind":"commodity","label":meta["label"],"category":meta["category"],"unit":meta["unit"],
                             "path":path,"start":hist[0]["date"],"end":hist[-1]["date"],"count":len(hist),"source":"Yahoo Finance"})
            series[t]=pd.Series([x["value"] for x in hist],index=pd.to_datetime([x["date"] for x in hist]))
        except Exception as e:
            manifest.append({"id":t,"kind":"commodity","label":meta["label"],"category":meta["category"],"unit":meta["unit"],
                             "path":None,"count":0,"error":type(e).__name__,"source":"Yahoo Finance"})

    # Historical intermarket ratios/spreads.
    derived={}
    pairs={
        "BRENT_WTI":("BZ=F","CL=F","Brent-WTI Spread","$/bbl","spread"),
        "GOLD_SILVER":("GC=F","SI=F","Gold/Silver Ratio","x","ratio"),
        "COPPER_GOLD":("HG=F","GC=F","Copper/Gold Ratio","x","ratio"),
    }
    for rid,(a,b,label,unit,mode) in pairs.items():
        if a not in series or b not in series:continue
        j=pd.concat([series[a].rename("a"),series[b].rename("b")],axis=1).dropna()
        vals=j["a"]-j["b"] if mode=="spread" else j["a"]/j["b"].replace(0,pd.NA)
        vals=vals.dropna()
        hist=[{"date":str(i.date()),"value":round(float(v),8)} for i,v in vals.items()]
        payload={"id":rid,"kind":"derived","source":"Derived from Yahoo futures","meta":{"label":label,"category":"Intermarket","unit":unit},"history":hist}
        path=f"history/commodities/{rid}.json"
        (outdir/f"{rid}.json").write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
        manifest.append({"id":rid,"kind":"derived","label":label,"category":"Intermarket","unit":unit,"path":path,
                         "start":hist[0]["date"],"end":hist[-1]["date"],"count":len(hist),"source":"Derived"})
    return manifest


def _eia_full(series:str):
    url=f"https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=W&n=PET&s={series}"
    r=requests.get(url,headers={"User-Agent":"RS-Radar history research"},timeout=45);r.raise_for_status()
    tables=pd.read_html(StringIO(r.text))
    if not tables:return []
    df=max(tables,key=lambda x:x.size);rows=[]
    for _,row in df.iterrows():
        cells=[str(x).strip() for x in row.tolist()]; ym=cells[0] if cells else ""
        m=re.search(r"(\d{4})-([A-Za-z]{3})",ym)
        if not m:continue
        year=int(m.group(1));mon=pd.to_datetime(m.group(2),format="%b").month
        for i in range(1,len(cells)-1,2):
            dm=re.search(r"(\d{2})/(\d{2})",cells[i])
            if not dm:continue
            try:
                dt=datetime(year,int(dm.group(1)),int(dm.group(2))).date()
                val=float(cells[i+1].replace(",","").strip())
            except Exception:continue
            rows.append({"date":dt.isoformat(),"value":val})
    return sorted({x["date"]:x for x in rows}.values(),key=lambda x:x["date"])


def build_eia_history(output_dir:str|Path):
    from .commodities_v9 import EIA_SERIES
    outdir=Path(output_dir);outdir.mkdir(parents=True,exist_ok=True);manifest=[]
    for key,meta in EIA_SERIES.items():
        try:
            hist=_eia_full(meta["series"])
            payload={"id":key,"kind":"eia","source":"U.S. EIA","meta":meta,"history":hist}
            (outdir/f"{key}.json").write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
            manifest.append({"id":key,"kind":"eia","label":meta["label"],"category":"Energy Inventory","unit":meta["unit"],
                             "path":f"history/eia/{key}.json","start":hist[0]["date"] if hist else None,"end":hist[-1]["date"] if hist else None,
                             "count":len(hist),"source":"U.S. EIA"})
        except Exception as e:
            manifest.append({"id":key,"kind":"eia","label":meta["label"],"category":"Energy Inventory","unit":meta["unit"],"path":None,"count":0,
                             "error":type(e).__name__,"source":"U.S. EIA"})
    return manifest


MARKET_TICKERS={
    "SPY":{"label":"S&P 500 ETF","category":"Market","unit":"$"},
    "^VIX":{"label":"VIX","category":"Market","unit":"index"},
    "^TNX":{"label":"US 10Y Yield Proxy","category":"Rates Market","unit":"index"},
    "DX-Y.NYB":{"label":"US Dollar Index","category":"FX","unit":"index"},
    "TLT":{"label":"20Y+ Treasury ETF","category":"Rates Market","unit":"$"},
    "HYG":{"label":"High Yield ETF","category":"Credit Market","unit":"$"},
    "BTC-USD":{"label":"Bitcoin","category":"Crypto","unit":"$"},
}

def build_market_history(output_dir:str|Path):
    import yfinance as yf
    outdir=Path(output_dir);outdir.mkdir(parents=True,exist_ok=True)
    tickers=list(MARKET_TICKERS)
    raw=yf.download(tickers,period="max",interval="1d",auto_adjust=True,repair=True,group_by="ticker",threads=True,progress=False)
    manifest=[]
    for t,meta in MARKET_TICKERS.items():
        try:
            d=raw[t].dropna(how="all")
            c=(d["Close"] if "Close" in d.columns else d["close"]).dropna()
            hist=[{"date":str(i.date()),"value":round(float(v),6)} for i,v in c.items()]
            if not hist:continue
            safe=t.replace("=","_").replace("^","_").replace("-","_")
            path=f"history/market/{safe}.json"
            payload={"id":t,"kind":"market","source":"Yahoo Finance via yfinance","meta":meta,"history":hist}
            (outdir/f"{safe}.json").write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
            manifest.append({"id":t,"kind":"market","label":meta["label"],"category":meta["category"],"unit":meta["unit"],
                             "path":path,"start":hist[0]["date"],"end":hist[-1]["date"],"count":len(hist),"source":"Yahoo Finance"})
        except Exception as e:
            manifest.append({"id":t,"kind":"market","label":meta["label"],"category":meta["category"],"unit":meta["unit"],
                             "path":None,"count":0,"error":type(e).__name__,"source":"Yahoo Finance"})
    return manifest

def build_calendar_archive(start_year=2019,end_year=None):
    end_year=end_year or date.today().year
    events=[]
    for y in range(start_year,end_year+1):
        try:events.extend(bls_events(y))
        except Exception:pass
        try:events.extend(fomc_events(y,include_past=True))
        except Exception:pass
        if y==date.today().year:
            try:events.extend(bea_events(y))
            except Exception:pass
    clean=[]
    for e in events:
        if not e.get("date"):continue
        clean.append(e)
    clean=sorted({(e["date"],e["title"],e.get("source")):e for e in clean}.values(),key=lambda x:(x["date"],x.get("time_et") or ""))
    return {"start_year":start_year,"end_year":end_year,"events":clean,
            "note":"Historical archive currently backfills official BLS schedules and FOMC dates where parseable; BEA current-year schedule is included. Daily runs preserve future additions."}


# Compatibility entrypoints also retain the last verified history on failed downloads.
# Production FRED/EIA collection uses the stricter dedicated adapters.
def _retaining_builder(build, registry, kind, folder):
    from ..reliability import read_json, atomic_json, store_history, valid_history, is_demo
    def wrapped(output_dir, *args, **kwargs):
        out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
        before={p.name:read_json(p,{}) for p in out.glob('*.json')}
        errors={};failure=None
        try:
            result=build(output_dir,*args,**kwargs)
            errors={x['id']:x.get('error') for x in result if x.get('error')}
        except Exception as e:failure=type(e).__name__
        after={p.name:read_json(p,{}) for p in out.glob('*.json')}
        mapping=dict(registry)
        if kind=='commodity':
            for d in after.values():
                if d.get('kind')=='derived':mapping[d['id']]=d.get('meta',{})
        manifest=[]
        for sid,meta in mapping.items():
            safe=sid.replace('=','_').replace('^','_')
            if kind=='market':safe=safe.replace('-','_')
            path=out/(safe+'.json');fresh=after.get(path.name)
            prior=before.get(path.name)
            if prior and not is_demo(prior) and valid_history(prior.get('history')):atomic_json(path,prior)
            elif path.exists():path.unlink()
            unchanged=fresh==prior
            d=store_history(path,None if unchanged else fresh,errors.get(sid) or failure or 'empty_download')
            h=d['history']
            manifest.append({'id':sid,'kind':fresh.get('kind',kind) if fresh else kind,**meta,'source':d.get('source','Yahoo Finance' if kind in {'market','commodity'} else 'U.S. EIA'),
                             'path':f'history/{folder}/{safe}.json' if h else None,'start':h[0]['date'] if h else None,'end':h[-1]['date'] if h else None,'count':len(h),
                             'status':d['status'],'last_attempt':d.get('last_attempt'),'last_success':d.get('last_success'),'error':d.get('error'),'refresh_frequency':'daily'})
        return manifest
    return wrapped

from .commodities_v9 import COMMODITIES, EIA_SERIES
build_commodity_history=_retaining_builder(build_commodity_history,COMMODITIES,'commodity','commodities')
build_market_history=_retaining_builder(build_market_history,MARKET_TICKERS,'market','market')
build_eia_history=_retaining_builder(build_eia_history,EIA_SERIES,'eia','eia')
