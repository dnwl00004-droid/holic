
from __future__ import annotations
from io import StringIO
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, math, re
import requests
import pandas as pd

FRED_CSV="https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
NYFED={
    "SOFR":"https://markets.newyorkfed.org/api/rates/secured/sofr/last/100.json",
    "EFFR":"https://markets.newyorkfed.org/api/rates/unsecured/effr/last/100.json",
}
GDP_NOW_URL="https://www.atlantafed.org/research-and-data/data/gdpnow/current-and-past-gdpnow-commentaries"
SERIES={
"DFF":{"label":"Effective Fed Funds Rate","category":"rates","unit":"%","transform":"level"},
"DGS2":{"label":"US Treasury 2Y","category":"rates","unit":"%","transform":"level"},
"DGS10":{"label":"US Treasury 10Y","category":"rates","unit":"%","transform":"level"},
"DGS30":{"label":"US Treasury 30Y","category":"rates","unit":"%","transform":"level"},
"T10Y2Y":{"label":"10Y-2Y Curve","category":"rates","unit":"pp","transform":"level"},
"T10Y3M":{"label":"10Y-3M Curve","category":"rates","unit":"pp","transform":"level"},
"DFII10":{"label":"10Y Real Yield","category":"rates","unit":"%","transform":"level"},
"T10YIE":{"label":"10Y Breakeven Inflation","category":"inflation","unit":"%","transform":"level"},
"CPIAUCSL":{"label":"CPI YoY","category":"inflation","unit":"%","transform":"yoy"},
"CPILFESL":{"label":"Core CPI YoY","category":"inflation","unit":"%","transform":"yoy"},
"PCEPILFE":{"label":"Core PCE YoY","category":"inflation","unit":"%","transform":"yoy"},
"UNRATE":{"label":"Unemployment Rate","category":"growth","unit":"%","transform":"level"},
"PAYEMS":{"label":"Payrolls 3M Change","category":"growth","unit":"k","transform":"diff3"},
"INDPRO":{"label":"Industrial Production YoY","category":"growth","unit":"%","transform":"yoy"},
"RSAFS":{"label":"Retail Sales YoY","category":"growth","unit":"%","transform":"yoy"},
"HOUST":{"label":"Housing Starts YoY","category":"growth","unit":"%","transform":"yoy"},
"WALCL":{"label":"Fed Total Assets","category":"liquidity","unit":"$bn","transform":"millions_to_bn"},
"RRPONTSYD":{"label":"Overnight Reverse Repo","category":"liquidity","unit":"$bn","transform":"level"},
"WRESBAL":{"label":"Bank Reserve Balances","category":"liquidity","unit":"$bn","transform":"millions_to_bn"},
"WTREGEN":{"label":"Treasury General Account","category":"liquidity","unit":"$bn","transform":"millions_to_bn"},
"M2SL":{"label":"M2 YoY","category":"liquidity","unit":"%","transform":"yoy"},
"BAMLH0A0HYM2":{"label":"US High Yield OAS","category":"credit","unit":"%","transform":"level"},
"BAMLC0A0CM":{"label":"US Corporate OAS","category":"credit","unit":"%","transform":"level"},
}
HEADERS={"User-Agent":"RS-Radar macro dashboard research"}

def _cache_file(cache_dir,name):
    p=Path(cache_dir);p.mkdir(parents=True,exist_ok=True);return p/f"{name}.json"

def _fresh(path,hours):
    if not path.exists():return False
    return datetime.now(timezone.utc)-datetime.fromtimestamp(path.stat().st_mtime,tz=timezone.utc)<timedelta(hours=hours)

def fetch_fred_series(series,cache_dir="data/cache/macro/fred",max_age_hours=8,session=None):
    cf=_cache_file(cache_dir,series)
    if _fresh(cf,max_age_hours):
        try:return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:pass
    s=session or requests.Session()
    r=s.get(FRED_CSV.format(series=series),headers=HEADERS,timeout=30);r.raise_for_status()
    df=pd.read_csv(StringIO(r.text));dc=df.columns[0];vc=series if series in df.columns else df.columns[-1]
    df[dc]=pd.to_datetime(df[dc],errors="coerce");df[vc]=pd.to_numeric(df[vc].replace(".",None),errors="coerce")
    df=df.dropna().sort_values(dc)
    rows=[{"date":d.strftime("%Y-%m-%d"),"value":float(v)} for d,v in zip(df[dc],df[vc])]
    out={"series":series,"rows":rows[-800:],"source":"FRED CSV","fetched_at":datetime.now(timezone.utc).isoformat()}
    cf.write_text(json.dumps(out,separators=(",",":")),encoding="utf-8");return out

def _nearest(rows,target):
    x=min(rows,key=lambda x:abs((pd.Timestamp(x["date"])-target).days)) if rows else None
    return x if x and abs((pd.Timestamp(x["date"])-target).days)<=50 else None

def _transform(rows,kind):
    if not rows:return None
    vals=[x["value"] for x in rows]
    if kind=="level":return vals[-1]
    if kind=="millions_to_bn":return vals[-1]/1000
    last=pd.Timestamp(rows[-1]["date"])
    if kind=="yoy":
        prev=_nearest(rows[:-1],last-pd.DateOffset(years=1))
        return None if not prev or prev["value"] in (0,None) else (vals[-1]/prev["value"]-1)*100
    if kind=="diff3":
        prev=_nearest(rows[:-1],last-pd.DateOffset(months=3))
        return None if not prev else vals[-1]-prev["value"]
    return vals[-1]

def _change(rows,months=3):
    if len(rows)<2:return None
    prev=_nearest(rows[:-1],pd.Timestamp(rows[-1]["date"])-pd.DateOffset(months=months))
    return None if not prev else rows[-1]["value"]-prev["value"]

def fred_macro_snapshot(session=None):
    out={}
    for sid,meta in SERIES.items():
        try:
            d=fetch_fred_series(sid,session=session);rows=d["rows"];value=_transform(rows,meta["transform"]);ch=_change(rows,3)
            out[sid]={**meta,"value":round(float(value),3) if value is not None and math.isfinite(float(value)) else None,
                      "date":rows[-1]["date"] if rows else None,"change_3m_raw":round(float(ch),3) if ch is not None else None,
                      "history":rows[-60:],"source":"FRED"}
        except Exception as e:
            out[sid]={**meta,"value":None,"error":type(e).__name__,"source":"FRED"}
    return out

def nyfed_reference_rates(session=None):
    s=session or requests.Session();out={}
    for name,url in NYFED.items():
        try:
            r=s.get(url,headers=HEADERS,timeout=30);r.raise_for_status();data=r.json().get("refRates",[])
            rows=[{"date":x.get("effectiveDate"),"rate":float(x["percentRate"]),
                   "volume_bn":float(x["volumeInBillions"]) if x.get("volumeInBillions") is not None else None}
                  for x in data if x.get("effectiveDate") and x.get("percentRate") is not None]
            rows=sorted(rows,key=lambda x:x["date"])
            out[name]={"value":rows[-1]["rate"] if rows else None,"date":rows[-1]["date"] if rows else None,
                       "volume_bn":rows[-1].get("volume_bn") if rows else None,"history":rows[-60:],
                       "source":"Federal Reserve Bank of New York"}
        except Exception as e:
            out[name]={"value":None,"error":type(e).__name__,"source":"Federal Reserve Bank of New York"}
    if out.get("SOFR",{}).get("value") is not None and out.get("EFFR",{}).get("value") is not None and out["SOFR"].get("date")==out["EFFR"].get("date"):
        out["SOFR_EFFR_SPREAD_BP"]={"value":round((out["SOFR"]["value"]-out["EFFR"]["value"])*100,1),
                                    "unit":"bp","date":out["SOFR"].get("date"),"source":"derived"}
    return out

def atlanta_gdpnow(session=None):
    s=session or requests.Session();r=s.get(GDP_NOW_URL,headers=HEADERS,timeout=30);r.raise_for_status()
    text=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",r.text))
    m=re.search(r"GDPNow model estimate for real GDP growth.*?quarter of (\d{4}) is (-?\d+(?:\.\d+)?) percent on ([A-Za-z]+ \d{1,2})",text,re.I)
    if not m:return {"value":None,"error":"parse_failed","source":"Atlanta Fed GDPNow"}
    return {"value":float(m.group(2)),"unit":"% SAAR","date_text":f"{m.group(3)}, {m.group(1)}","source":"Federal Reserve Bank of Atlanta GDPNow"}
