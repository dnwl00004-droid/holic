
from __future__ import annotations
from datetime import date
from pathlib import Path
import json
import pandas as pd

def load_log(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_log(path: str | Path, rows: list[dict]):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

def update_signal_log(log, records, prices, as_of):
    """Log NEW setup detections once; later resolve 20-trading-day outcomes."""
    active = {(r.get("ticker"), r.get("pattern"), r.get("signal_date")) for r in log}
    last_by_ticker_pattern = {}
    for r in log:
        key=(r.get("ticker"), r.get("pattern"))
        if key not in last_by_ticker_pattern or (r.get("signal_date") or "") > (last_by_ticker_pattern[key].get("signal_date") or ""):
            last_by_ticker_pattern[key]=r

    for rec in records:
        pat=rec.get("patterns",{}).get("primary")
        if not pat:
            continue
        key=(rec["ticker"],pat)
        prev=last_by_ticker_pattern.get(key)
        # Don't duplicate a continuously-active setup within 10 calendar days.
        duplicate=False
        if prev:
            try:
                duplicate=(pd.Timestamp(as_of)-pd.Timestamp(prev["signal_date"])).days < 10
            except Exception:
                pass
        if not duplicate:
            log.append({
                "ticker":rec["ticker"],"pattern":pat,"signal_date":as_of,
                "entry_price":rec["price"]["close"],"strength":rec["scores"]["strength"],
                "setup":rec["scores"]["setup"],"resolved":False
            })

    # Resolve using the locally downloaded history.
    for sig in log:
        if sig.get("resolved"):
            continue
        t=sig["ticker"].replace(".","-")
        df=prices.get(t)
        if df is None or df.empty:
            continue
        idx=pd.DatetimeIndex(df.index).tz_localize(None)
        start=pd.Timestamp(sig["signal_date"])
        future=df.loc[idx >= start].copy()
        if len(future) < 21:
            continue
        entry=float(sig["entry_price"])
        closes=future["close"].iloc[:21]
        sig["return_20d_pct"]=round((float(closes.iloc[-1])/entry-1)*100,2)
        sig["max_move_20d_pct"]=round((float(closes.max())/entry-1)*100,2)
        sig["max_drawdown_20d_pct"]=round((float(closes.min())/entry-1)*100,2)
        sig["success"]=sig["return_20d_pct"] > 0
        sig["resolved"]=True
    return log

def scorecard(log):
    done=[x for x in log if x.get("resolved")]
    if not done:
        return {"resolved":0,"win_rate":None,"avg_20d":None,"avg_max_move":None,"avg_drawdown":None}
    wins=sum(bool(x.get("success")) for x in done)
    avg=lambda k: round(sum(float(x.get(k,0)) for x in done)/len(done),2)
    return {
        "resolved":len(done),
        "win_rate":round(wins/len(done)*100,1),
        "avg_20d":avg("return_20d_pct"),
        "avg_max_move":avg("max_move_20d_pct"),
        "avg_drawdown":avg("max_drawdown_20d_pct"),
    }

def today_changes(previous, records):
    if not previous:
        return []
    prev={x["ticker"]:x for x in previous.get("tickers",[])}
    out=[]
    for x in records:
        p=prev.get(x["ticker"])
        if not p: continue
        changes=[]
        oldpat=p.get("patterns",{}).get("primary")
        newpat=x.get("patterns",{}).get("primary")
        if not oldpat and newpat: changes.append(f"New {newpat}")
        oq=p.get("rs",{}).get("quadrant"); nq=x.get("rs",{}).get("quadrant")
        if oq!=nq: changes.append(f"{oq or '—'} → {nq or '—'}")
        ors=p.get("rs",{}).get("score"); nrs=x.get("rs",{}).get("score")
        if ors is not None and nrs is not None and abs(nrs-ors)>=3: changes.append(f"RS {ors} → {nrs}")
        os=p.get("scores",{}).get("setup"); ns=x.get("scores",{}).get("setup")
        if os is not None and ns is not None and abs(ns-os)>=8: changes.append(f"Setup {os} → {ns}")
        if changes:
            out.append({"ticker":x["ticker"],"changes":changes,"priority":len(changes)+(2 if newpat and not oldpat else 0)})
    return sorted(out,key=lambda z:z["priority"],reverse=True)[:30]
