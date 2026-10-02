
from __future__ import annotations
import numpy as np
import pandas as pd

def rs_new_high_signal(stock: pd.Series, benchmark: pd.Series, window: int=252) -> dict:
    j=pd.concat([stock.rename("s"),benchmark.rename("b")],axis=1).dropna()
    if len(j)<window:return {"rs_new_high":False,"before_price":False}
    j=j.tail(window)
    rs=j["s"]/j["b"]
    rs_new=bool(rs.iloc[-1] >= rs.max()*0.995)
    price_new=bool(j["s"].iloc[-1] >= j["s"].max()*0.995)
    return {"rs_new_high":rs_new,"before_price":bool(rs_new and not price_new),
            "rs_line_52w_position":round(float(rs.iloc[-1]/rs.max()*100),2),
            "price_52w_position":round(float(j["s"].iloc[-1]/j["s"].max()*100),2)}

def multi_screeners(rec: dict, volume_break: dict, rsnh: dict) -> dict:
    t=rec.get("trend_template",{})
    rs=rec.get("rs",{}).get("score") or 0
    stage=rec.get("stage",{}).get("value")
    earn=rec.get("earnings",{})
    eps=earn.get("eps_growth_yoy")
    rev=earn.get("revenue_growth_yoy")
    risk=rec.get("risk",{})
    vcp=rec.get("patterns",{}).get("vcp",{})

    minervini_like = t.get("passed",0)>=7 and rs>=70 and stage==2
    growth_leader = (
        (eps is not None and eps>=25) and
        (rev is not None and rev>=15) and rs>=70 and stage==2
    )
    vcp_ready = bool(vcp.get("detected") and (vcp.get("score") or 0)>=70)
    clean_trend = t.get("passed",0)>=7 and len(rec.get("warnings",[]))==0

    flags={
        "trend_leader":bool(minervini_like),
        "growth_leader":bool(growth_leader),
        "vcp_ready":bool(vcp_ready),
        "volume_breakthrough":bool(volume_break.get("detected")),
        "rs_new_high":bool(rsnh.get("rs_new_high")),
        "rs_new_high_before_price":bool(rsnh.get("before_price")),
        "clean_trend":bool(clean_trend),
    }
    return {"flags":flags,"count":sum(flags.values())}

def group_rankings(records: list[dict]) -> list[dict]:
    groups={}
    for r in records: groups.setdefault(r.get("sector","Unknown"),[]).append(r)
    rows=[]
    for name,arr in groups.items():
        avg=lambda vals: round(sum(vals)/len(vals),2) if vals else None
        rets=lambda k:[x.get("period_returns",{}).get(k) for x in arr if x.get("period_returns",{}).get(k) is not None]
        above50=sum(1 for x in arr if x.get("price",{}).get("close",0)>x.get("price",{}).get("sma50",1e99))
        above200=sum(1 for x in arr if x.get("price",{}).get("close",0)>x.get("price",{}).get("sma200",1e99))
        rows.append({
            "group":name,"count":len(arr),
            "avg_rs":avg([x.get("rs",{}).get("score",0) or 0 for x in arr]),
            "avg_short_rs":avg([x.get("rs",{}).get("short",0) or 0 for x in arr]),
            "return_1m":avg(rets("1M")),"return_3m":avg(rets("3M")),
            "above50_pct":round(100*above50/len(arr),1),
            "above200_pct":round(100*above200/len(arr),1),
            "setup_count":sum(bool(x.get("patterns",{}).get("primary")) for x in arr),
            "ready_count":sum(x.get("entry",{}).get("label")=="READY" for x in arr),
        })
    # group score prioritizes RS + participation + recent return
    for r in rows:
        r["score"]=round(
            (r["avg_rs"] or 0)*.45 +
            (r["avg_short_rs"] or 0)*.20 +
            (r["above50_pct"] or 0)*.20 +
            max(0,min(100,50+(r["return_1m"] or 0)*4))*.15, 1
        )
    rows.sort(key=lambda x:x["score"],reverse=True)
    for i,r in enumerate(rows,1): r["rank"]=i
    return rows
