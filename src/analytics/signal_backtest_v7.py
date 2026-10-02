
from __future__ import annotations
import numpy as np
import pandas as pd

def _forward(df,i,h):
    if i+h>=len(df): return None
    # Signal is known after the close; execution is the NEXT session open.
    if "open" not in df or not np.isfinite(df["open"].iloc[i+1]): return None
    entry=float(df["open"].iloc[i+1]); exit_=float(df["close"].iloc[i+h])
    if entry <= 0: return None
    w=df["close"].iloc[i+1:i+h+1]
    peak=np.maximum.accumulate(np.r_[entry,w.to_numpy()])
    drawdown=float(np.min(np.r_[entry,w.to_numpy()]/peak-1))*100
    return {
        "return_pct":(exit_/entry-1)*100,
        "max_move_pct":(float(w.max())/entry-1)*100,
        "max_drawdown_pct":drawdown,
        "max_adverse_excursion_pct":min(0,(float(w.min())/entry-1)*100),
    }

def _rs_before_price(df,bm,i,window=252):
    d=df.iloc[:i+1]
    end=d.index[-1]
    b=bm.loc[:end]
    if len(d)<window or len(b)<window:return False
    joined=pd.concat([d["close"].rename("s"),b["close"].rename("b")],axis=1).dropna().tail(window)
    if len(joined)<window*.9:return False
    rs=joined["s"]/joined["b"]
    rs_new=rs.iloc[-1]>=rs.max()*.995
    price_new=joined["s"].iloc[-1]>=joined["s"].max()*.995
    return bool(rs_new and not price_new)

def _volume_break(df,i):
    if i<21:return False
    ret=float(df["close"].iloc[i]/df["close"].iloc[i-1]-1)
    prior=float(df["volume"].iloc[i-20:i].mean())
    rel=float(df["volume"].iloc[i]/max(prior,1))
    return bool(ret>=.02 and rel>=1.5)

def _trend_leader(df,i):
    if i<252:return False
    c=df["close"].iloc[:i+1].dropna()
    if len(c)<252:return False
    px=float(c.iloc[-1]); ma50=float(c.tail(50).mean());ma150=float(c.tail(150).mean());ma200=float(c.tail(200).mean())
    ma200_old=float(c.iloc[-220:-20].tail(200).mean()) if len(c)>=220 else ma200
    checks=[
        px>ma150 and px>ma200, ma150>ma200, ma200>ma200_old,
        ma50>ma150 and ma50>ma200, px>ma50,
        px>=float(c.tail(252).min())*1.30, px>=float(c.tail(252).max())*.75,
    ]
    return sum(checks)>=6

DETECTORS={
    "RS_BEFORE_PRICE":_rs_before_price,
    "VOLUME_BREAK":lambda df,bm,i:_volume_break(df,i),
    "TREND_LEADER":lambda df,bm,i:_trend_leader(df,i),
}

def _vcp(df,bm,i):
    from .patterns import vcp_proxy
    return bool(vcp_proxy(df.iloc[:i+1]).get("detected"))

def _entry_ready(df,bm,i):
    from .patterns import vcp_proxy
    from .technicals_plus import entry_timing_score
    window=df.iloc[:i+1]
    return entry_timing_score(window,vcp_proxy(window)).get("label")=="READY"

DETECTORS.update(VCP=_vcp,ENTRY_READY=_entry_ready)

def backtest_signals(df:pd.DataFrame,bm:pd.DataFrame,horizons=(5,20,60),cooldown=10):
    results={}
    for name,det in DETECTORS.items():
        events=[];last=-999
        max_h=max(horizons)
        for i in range(260,len(df)-max_h):
            if i-last<cooldown:continue
            try:active=det(df,bm,i)
            except Exception:active=False
            if not active:continue
            e={"date":str(df.index[i].date()),"execution_date":str(df.index[i+1].date()),"price":round(float(df["open"].iloc[i+1]),2) if "open" in df else None}
            for h in horizons:
                z=_forward(df,i,h)
                if z:
                    e[f"ret_{h}d_pct"]=round(z["return_pct"],2)
                    e[f"max_{h}d_pct"]=round(z["max_move_pct"],2)
                    e[f"dd_{h}d_pct"]=round(z["max_drawdown_pct"],2)
            events.append(e);last=i
        results[name]=score_events(events,horizons)
    return results

def score_events(events,horizons=(5,20,60)):
    out={"count":len(events),"events":events[-12:],"all_events":events,"execution":"next-session open; exit horizon counted from signal session","limitations":["current-universe survivorship bias","overlapping forward windows","adjusted historical prices; no fees or slippage","technical-only data; revised macro not used"]}
    for h in horizons:
        vals=[e.get(f"ret_{h}d_pct") for e in events if e.get(f"ret_{h}d_pct") is not None]
        if not vals:
            out[f"{h}d"]={"count":0,"win_rate":None,"avg_return_pct":None,"median_return_pct":None}
            continue
        out[f"{h}d"]={
            "count":len(vals),
            "win_rate":round(100*sum(v>0 for v in vals)/len(vals),1),
            "avg_return_pct":round(float(np.mean(vals)),2),
            "median_return_pct":round(float(np.median(vals)),2),
            "avg_max_move_pct":round(float(np.mean([e[f"max_{h}d_pct"] for e in events if e.get(f"max_{h}d_pct") is not None])),2),
            "avg_drawdown_pct":round(float(np.mean([e[f"dd_{h}d_pct"] for e in events if e.get(f"dd_{h}d_pct") is not None])),2),
        }
    return out

def aggregate_signal_results(per_ticker:dict[str,dict],horizons=(5,20,60)):
    out={}
    for sig in DETECTORS:
        events=[]
        for t,data in per_ticker.items():
            for e in data.get(sig,{}).get("all_events",data.get(sig,{}).get("events",[])):
                events.append({"ticker":t,**e})
        out[sig]=score_events(events,horizons)
        out[sig]["events"]=sorted(events,key=lambda x:x["date"],reverse=True)[:30]
    return out
