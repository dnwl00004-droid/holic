from __future__ import annotations
import math
from io import StringIO
from datetime import datetime, timezone
import pandas as pd
import requests
import yfinance as yf

COMMODITIES={
    # Energy
    "CL=F":{"label":"WTI Crude","category":"Energy","unit":"$/bbl"},
    "BZ=F":{"label":"Brent Crude","category":"Energy","unit":"$/bbl"},
    "NG=F":{"label":"Natural Gas","category":"Energy","unit":"$/MMBtu"},
    "RB=F":{"label":"RBOB Gasoline","category":"Energy","unit":"$/gal"},
    "HO=F":{"label":"Heating Oil","category":"Energy","unit":"$/gal"},
    # Metals
    "GC=F":{"label":"Gold","category":"Metals","unit":"$/oz"},
    "SI=F":{"label":"Silver","category":"Metals","unit":"$/oz"},
    "HG=F":{"label":"Copper","category":"Metals","unit":"$/lb"},
    "PL=F":{"label":"Platinum","category":"Metals","unit":"$/oz"},
    "PA=F":{"label":"Palladium","category":"Metals","unit":"$/oz"},
    "TIO=F":{"label":"Iron Ore 62% Fe","category":"Metals","unit":"$/t","optional":True},
    # Agriculture
    "ZC=F":{"label":"Corn","category":"Agriculture","unit":"¢/bu"},
    "ZW=F":{"label":"Wheat","category":"Agriculture","unit":"¢/bu"},
    "ZS=F":{"label":"Soybeans","category":"Agriculture","unit":"¢/bu"},
    "KC=F":{"label":"Coffee","category":"Agriculture","unit":"¢/lb"},
    "CC=F":{"label":"Cocoa","category":"Agriculture","unit":"$/t"},
    "SB=F":{"label":"Sugar #11","category":"Agriculture","unit":"¢/lb"},
    "CT=F":{"label":"Cotton","category":"Agriculture","unit":"¢/lb"},
    "LE=F":{"label":"Live Cattle","category":"Agriculture","unit":"¢/lb"},
}

EIA_SERIES={
    "crude_ex_spr":{"label":"Crude Oil ex-SPR","series":"WCESTUS1","unit":"thousand bbl"},
    "total_crude":{"label":"Total Crude Oil","series":"WCRSTUS1","unit":"thousand bbl"},
    "gasoline":{"label":"Total Gasoline","series":"WGTSTUS1","unit":"thousand bbl"},
    "distillate":{"label":"Distillate Fuel Oil","series":"WDISTUS1","unit":"thousand bbl"},
}


def _ret(c,n):
    return None if len(c)<=n else (float(c.iloc[-1]/c.iloc[-1-n])-1)*100


def commodity_snapshot(period="2y"):
    tickers=list(COMMODITIES)
    raw=yf.download(tickers,period=period,interval="1d",auto_adjust=True,repair=True,group_by="ticker",threads=True,progress=False)
    out={}
    closes={}
    for t,meta in COMMODITIES.items():
        try:
            d=raw[t].dropna(how="all")
            c=d["Close"].dropna() if "Close" in d.columns else d["close"].dropna()
            if len(c)<25: continue
            closes[t]=c
            last=float(c.iloc[-1]); ma20=float(c.tail(20).mean()); ma50=float(c.tail(50).mean()) if len(c)>=50 else None
            hi52=float(c.tail(252).max()) if len(c)>=252 else float(c.max())
            lo52=float(c.tail(252).min()) if len(c)>=252 else float(c.min())
            pos=100*(last-lo52)/max(hi52-lo52,1e-9)
            vol=float(c.pct_change().tail(20).std()*math.sqrt(252)*100)
            out[t]={**meta,"value":round(last,4),"date":str(c.index[-1].date()),
                    "return_1d_pct":round(_ret(c,1),2),"return_1w_pct":round(_ret(c,5),2) if _ret(c,5) is not None else None,
                    "return_1m_pct":round(_ret(c,21),2) if _ret(c,21) is not None else None,
                    "return_3m_pct":round(_ret(c,63),2) if _ret(c,63) is not None else None,
                    "return_12m_pct":round(_ret(c,252),2) if _ret(c,252) is not None else None,
                    "above_20dma":bool(last>ma20),"above_50dma":bool(ma50 is not None and last>ma50),
                    "position_52w_pct":round(pos,1),"volatility20_ann_pct":round(vol,1),
                    "history":[{"date":str(i.date()),"value":round(float(v),4)} for i,v in c.tail(120).items()],
                    "source":"Yahoo Finance via yfinance"}
        except Exception: continue

    def last(t):
        return out.get(t,{}).get("value")
    derived={}
    if last("BZ=F") is not None and last("CL=F") is not None:
        derived["brent_wti_spread"]={"label":"Brent-WTI Spread","value":round(last("BZ=F")-last("CL=F"),2),"unit":"$/bbl"}
    if last("GC=F") and last("SI=F"):
        derived["gold_silver_ratio"]={"label":"Gold/Silver Ratio","value":round(last("GC=F")/last("SI=F"),2),"unit":"x"}
    if last("HG=F") and last("GC=F"):
        derived["copper_gold_ratio"]={"label":"Copper/Gold Ratio","value":round(last("HG=F")/last("GC=F"),6),"unit":"x"}
    valid=list(out.values())
    breadth={
        "count":len(valid),
        "above_50dma_pct":round(100*sum(bool(x.get("above_50dma")) for x in valid)/len(valid),1) if valid else None,
        "positive_1m_pct":round(100*sum((x.get("return_1m_pct") or 0)>0 for x in valid)/len(valid),1) if valid else None,
        "energy_3m_avg_pct":round(sum(x.get("return_3m_pct") or 0 for x in valid if x.get("category")=="Energy")/max(1,sum(x.get("category")=="Energy" for x in valid)),2) if valid else None,
    }
    return {"contracts":out,"derived":derived,"breadth":breadth}


def _extract_eia_history(series):
    url=f"https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=W&n=PET&s={series}"
    r=requests.get(url,headers={"User-Agent":"RS-Radar research"},timeout=35); r.raise_for_status()
    tables=pd.read_html(StringIO(r.text))
    if not tables: return []
    df=max(tables,key=lambda x:x.size)
    rows=[]
    current_year=None
    for _,row in df.iterrows():
        cells=[str(x).strip() for x in row.tolist()]
        ym=cells[0] if cells else ""
        m=pd.Series([ym]).str.extract(r"(\d{4})-([A-Za-z]{3})").iloc[0]
        if m.notna().all():
            year=int(m.iloc[0]); mon=pd.to_datetime(m.iloc[1],format="%b").month
        else:
            continue
        for i in range(1,len(cells)-1,2):
            ds=cells[i]; vs=cells[i+1]
            dm=pd.Series([ds]).str.extract(r"(\d{2})/(\d{2})").iloc[0]
            if not dm.notna().all(): continue
            try:
                dt=datetime(year,int(dm.iloc[0]),int(dm.iloc[1])).date()
                val=float(str(vs).replace(",","").replace("nan","").strip())
            except Exception: continue
            rows.append({"date":dt.isoformat(),"value":val})
    rows=sorted({x["date"]:x for x in rows}.values(),key=lambda x:x["date"])
    return rows[-80:]


def eia_inventory_snapshot():
    out={}
    for key,meta in EIA_SERIES.items():
        try:
            hist=_extract_eia_history(meta["series"])
            if not hist: raise ValueError("no rows")
            latest=hist[-1]["value"]; prev=hist[-2]["value"] if len(hist)>1 else None
            avg5=sum(x["value"] for x in hist[-5:])/min(5,len(hist))
            avg52=sum(x["value"] for x in hist[-52:])/min(52,len(hist))
            out[key]={**meta,"value":latest,"date":hist[-1]["date"],
                      "weekly_change":round(latest-prev,1) if prev is not None else None,
                      "vs_5w_avg_pct":round((latest/avg5-1)*100,2) if avg5 else None,
                      "vs_52w_avg_pct":round((latest/avg52-1)*100,2) if avg52 else None,
                      "history":hist,"source":"U.S. EIA weekly petroleum data"}
        except Exception as e:
            out[key]={**meta,"value":None,"error":type(e).__name__,"source":"U.S. EIA weekly petroleum data"}
    return out
