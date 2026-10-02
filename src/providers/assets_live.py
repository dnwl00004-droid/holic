"""Validated daily asset histories, retaining full verified data on provider failure."""
from __future__ import annotations
import math
from pathlib import Path
import pandas as pd
from .commodities_v9 import COMMODITIES
from .history_v10 import MARKET_TICKERS
from .yahoo import download_daily
from ..reliability import read_json, store_history


def summarize(history):
    """Trading-session returns and risk metrics; absent lookbacks stay null."""
    if not history: return {"value": None, "date": None}
    values = pd.Series([r["value"] for r in history], dtype=float)
    last = float(values.iloc[-1])
    def ret(days):
        if len(values) <= days or values.iloc[-days-1] <= 0: return None
        return round((last / values.iloc[-days-1] - 1) * 100, 4)
    result = {"value": last, "date": history[-1]["date"], "history": history[-120:]}
    for key, days in (("1d",1),("1w",5),("1m",21),("3m",63),("6m",126),("12m",252)):
        result[f"return_{key}_pct"] = ret(days)
    for days in (20,50,200):
        ma = float(values.tail(days).mean()) if len(values) >= days else None
        result[f"ma{days}"] = ma
        result[f"above_{days}dma"] = last > ma if ma is not None else None
    hi = float(values.tail(252).max()) if len(values) >= 252 else None
    lo = float(values.tail(252).min()) if len(values) >= 252 else None
    result.update(high_52w=hi, low_52w=lo,
                  position_52w_pct=(last-lo)/(hi-lo)*100 if hi is not None and hi != lo else None,
                  volatility20_ann_pct=float(values.pct_change(fill_method=None).tail(20).std()*math.sqrt(252)*100) if len(values)>20 and (values.tail(21)>0).all() else None)
    return result


def collect_assets(root, fetch=download_daily):
    root = Path(root)
    registry = {**{k:{**v,"kind":"commodity"} for k,v in COMMODITIES.items()},
                **{k:{**v,"kind":"market"} for k,v in MARKET_TICKERS.items()}}
    try:
        frames = fetch(list(registry), period="max")
        fetch_error = None
    except Exception as e:
        frames = {}; fetch_error = type(e).__name__
    items = []; contracts = {}; market = {}
    for sid, meta in registry.items():
        folder = "commodities" if meta["kind"] == "commodity" else "market"
        name = sid.replace("=","_").replace("^","_").replace("-","_") + ".json"
        path = root/folder/name; payload = None
        try:
            frame = frames.get(sid)
            if frame is not None and not frame.empty:
                close = frame["close"].dropna()
                history = [{"date":str(dt.date()),"value":float(v)} for dt,v in close.items()]
                payload = {"id":sid,"kind":meta["kind"],"meta":meta,"source":"Yahoo Finance via yfinance",
                           "source_url":"https://finance.yahoo.com/quote/"+sid,"history":history,
                           "method":"daily adjusted close; trading-session lookbacks",
                           "caveat":"Front-month futures have contract-roll effects." if meta["kind"]=="commodity" else "Adjusted historical prices."}
        except (KeyError,TypeError,ValueError): pass
        data = store_history(path,payload,fetch_error or "provider_returned_no_valid_observations")
        history = data["history"]
        item = {"id":sid,**meta,"source":"Yahoo Finance", "path":f"history/{folder}/{name}" if history else None,
                "count":len(history),"start":history[0]["date"] if history else None,"end":history[-1]["date"] if history else None,
                "status":data["status"],"last_attempt":data.get("last_attempt"),"last_success":data.get("last_success"),"error":data.get("error"),
                "method":"daily adjusted close; trading-session lookbacks","refresh_frequency":"daily after US close"}
        items.append(item)
        value = {**meta,**summarize(history),"source":item["source"],"source_url":payload["source_url"] if payload else data.get("source_url"),
                 "status":item["status"],"last_update":item["last_success"],"error":item["error"],"method":item["method"]}
        (contracts if meta["kind"]=="commodity" else market)[sid] = value
    available = [x for x in contracts.values() if x["value"] is not None]
    above = [x for x in available if x.get("above_50dma") is not None]
    positive = [x for x in available if x.get("return_1m_pct") is not None]
    energy = [x["return_3m_pct"] for x in available if x["category"]=="Energy" and x.get("return_3m_pct") is not None]
    breadth = {"count":len(available),"above_50dma_pct":sum(x["above_50dma"] for x in above)/len(above)*100 if above else None,
               "positive_1m_pct":sum(x["return_1m_pct"]>0 for x in positive)/len(positive)*100 if positive else None,
               "energy_3m_avg_pct":sum(energy)/len(energy) if energy else None}
    # Same-date joins avoid ratios between unrelated observation dates.
    derived = {}
    for key,a,b,mode,label,unit in (("brent_wti_spread","BZ=F","CL=F","spread","Brent-WTI Spread","$/bbl"),
        ("gold_silver_ratio","GC=F","SI=F","ratio","Gold/Silver Ratio","x"),("copper_gold_ratio","HG=F","GC=F","ratio","Copper/Gold Ratio","x")):
        left = contracts[a].get("history",[]); right = {r["date"]:r["value"] for r in contracts[b].get("history",[])}
        common = [r for r in left if r["date"] in right and (mode=="spread" or right[r["date"]]!=0)]
        last = common[-1] if common else None
        derived[key] = {"label":label,"unit":unit,"date":last["date"] if last else None,
                        "value":(last["value"]-right[last["date"]] if mode=="spread" else last["value"]/right[last["date"]]) if last else None,
                        "method":"same-date futures "+mode}
    return items, {"contracts":contracts,"derived":derived,"breadth":breadth}, market
