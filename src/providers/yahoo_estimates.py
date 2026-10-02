
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, math
import yfinance as yf
import pandas as pd

def _finite(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except Exception:return None

def _df_row(df, idx):
    try:
        if df is None or len(df)==0:return {}
        row=df.loc[idx]
        if hasattr(row,"to_dict"):row=row.to_dict()
        return {str(k):_finite(v) if isinstance(v,(int,float)) or str(v).replace(".","",1).replace("-","",1).isdigit() else v for k,v in row.items()}
    except Exception:return {}

def _cache_path(ticker,cache_dir):
    p=Path(cache_dir);p.mkdir(parents=True,exist_ok=True)
    return p/f"{ticker.replace('.','-').upper()}.json"

def estimate_snapshot(ticker:str, cache_dir="data/cache/yahoo_analysis", max_age_hours=18):
    p=_cache_path(ticker,cache_dir)
    if p.exists():
        age=datetime.now(timezone.utc)-datetime.fromtimestamp(p.stat().st_mtime,tz=timezone.utc)
        if age<timedelta(hours=max_age_hours):
            try:return json.loads(p.read_text(encoding="utf-8"))
            except Exception:pass

    t=yf.Ticker(ticker)
    out={"source":"Yahoo Finance via yfinance"}

    # Market cap / shares
    try:
        fi=t.fast_info
        out["market_cap"]=_finite(fi.get("market_cap") if hasattr(fi,"get") else getattr(fi,"market_cap",None))
    except Exception:out["market_cap"]=None
    try:
        sh=t.get_shares_full()
        if sh is not None and len(sh):
            out["shares_outstanding"]=_finite(sh.dropna().iloc[-1])
        else:out["shares_outstanding"]=None
    except Exception:out["shares_outstanding"]=None

    try: trend=t.get_eps_trend()
    except Exception: trend=None
    try: revisions=t.get_eps_revisions()
    except Exception: revisions=None
    try: est=t.get_earnings_estimate()
    except Exception: est=None
    try: rev_est=t.get_revenue_estimate()
    except Exception: rev_est=None
    try: hist=t.get_earnings_history()
    except Exception: hist=None
    try: cal=t.get_calendar()
    except Exception: cal={}

    out["eps_trend"]={k:_df_row(trend,k) for k in ["0q","+1q","0y","+1y"]}
    out["eps_revisions"]={k:_df_row(revisions,k) for k in ["0q","+1q","0y","+1y"]}
    out["earnings_estimate"]={k:_df_row(est,k) for k in ["0q","+1q","0y","+1y"]}
    out["revenue_estimate"]={k:_df_row(rev_est,k) for k in ["0q","+1q","0y","+1y"]}

    # Revision pulse from next-year EPS current vs 30/90d ago.
    tr=out["eps_trend"].get("+1y") or out["eps_trend"].get("0y") or {}
    cur=_finite(tr.get("current")); d30=_finite(tr.get("30daysAgo")); d90=_finite(tr.get("90daysAgo"))
    out["revision_pulse"]={
        "eps_current":cur,"eps_30d_ago":d30,"eps_90d_ago":d90,
        "change_30d_pct":round((cur/d30-1)*100,2) if cur is not None and d30 not in (None,0) else None,
        "change_90d_pct":round((cur/d90-1)*100,2) if cur is not None and d90 not in (None,0) else None,
    }
    rv=out["eps_revisions"].get("+1y") or out["eps_revisions"].get("0y") or {}
    up30=_finite(rv.get("upLast30days"));down30=_finite(rv.get("downLast30days"))
    out["revision_pulse"]["up_30d"]=int(up30) if up30 is not None else None;out["revision_pulse"]["down_30d"]=int(down30) if down30 is not None else None
    out["revision_pulse"]["net_30d"]=int(up30-down30) if up30 is not None and down30 is not None else None

    # Historical surprises
    surprises=[]
    if hist is not None:
        try:
            for idx,row in hist.tail(8).iterrows():
                sp=_finite(row.get("surprisePercent"))
                surprises.append({"date":str(getattr(idx,"date",lambda:idx)()),
                                  "estimate":_finite(row.get("epsEstimate")),
                                  "actual":_finite(row.get("epsActual")),
                                  "surprise_pct":round(sp,2) if sp is not None else None})
        except Exception:pass
    vals=[x["surprise_pct"] for x in surprises if x["surprise_pct"] is not None]
    out["earnings_surprises"]=surprises
    out["surprise_summary"]={
        "last_surprise_pct":vals[-1] if vals else None,
        "avg_last4_pct":round(sum(vals[-4:])/len(vals[-4:]),2) if vals else None,
        "positive_last4":sum(v>0 for v in vals[-4:]) if vals else None,
    }

    # Next earnings date, when exposed
    dates=None
    if isinstance(cal,dict):
        dates=cal.get("Earnings Date") or cal.get("earningsDate")
    if isinstance(dates,(list,tuple)) and dates:
        dates=str(dates[0])
    elif dates is not None:
        dates=str(dates)
    out["next_earnings"]=dates

    out["fetched_at"]=datetime.now(timezone.utc).isoformat()
    if cur is None and not surprises and out.get("market_cap") is None:
        out.update(status="unavailable",error="no verified estimate or price inputs")
        if p.exists():
            try:
                old=json.loads(p.read_text())
                if old.get("status")!="unavailable":return {**old,"status":"stale","error":out["error"],"last_attempt":out["fetched_at"]}
            except Exception:pass
    else:out["status"]="ok"
    from ..reliability import atomic_json
    atomic_json(p,out)
    return out
