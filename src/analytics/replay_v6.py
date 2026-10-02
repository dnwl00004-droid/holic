
from __future__ import annotations
import math
import numpy as np
import pandas as pd

def _score_at(df:pd.DataFrame, benchmark:pd.DataFrame, end:int):
    """
    Price/volume-only score recomputed using bars available at `end`.
    Avoids today's fundamentals. Current-universe survivorship bias remains.
    """
    d=df.iloc[:end+1]
    b=benchmark.loc[:d.index[-1]]
    if len(d)<260 or len(b)<260:return None
    c=d["close"].dropna(); bc=b["close"].dropna()
    if len(c)<260 or len(bc)<260:return None
    # weighted momentum raw; absolute proxy in replay, not cross-sectional percentile
    ret=lambda n: float(c.iloc[-1]/c.iloc[-1-n]-1)
    mom=.40*ret(63)+.20*ret(126)+.20*ret(189)+.20*ret(252)
    rel=(c/bc.reindex(c.index).ffill()).dropna()
    short=float(rel.iloc[-1]/rel.iloc[-22]-1) if len(rel)>22 else 0
    ma50=float(c.tail(50).mean());ma150=float(c.tail(150).mean());ma200=float(c.tail(200).mean())
    trend=sum([
        c.iloc[-1]>ma150 and c.iloc[-1]>ma200,
        ma150>ma200,
        ma200>float(c.iloc[-220:-20].tail(200).mean()) if len(c)>=220 else False,
        ma50>ma150 and ma50>ma200,
        c.iloc[-1]>ma50,
        c.iloc[-1]>=float(c.tail(252).min())*1.30,
        c.iloc[-1]>=float(c.tail(252).max())*.75,
    ])
    # score deliberately avoids percentile rank to make single-name point-in-time replay cheap
    mom_score=max(0,min(100,50+mom*120))
    short_score=max(0,min(100,50+short*250))
    trend_score=trend/7*100
    score=.55*mom_score+.20*short_score+.25*trend_score
    return {"score":round(score,1),"momentum":round(mom*100,2),"short_relative":round(short*100,2),"trend_pass":trend}

def backtest_price_signal(df, benchmark, threshold=75, hold_days=20, step=5):
    """
    Weekly-spaced signal replay. A signal occurs when price-only score crosses threshold.
    """
    trades=[]
    prev_above=False
    for i in range(260,len(df)-hold_days,step):
        s=_score_at(df,benchmark,i)
        if not s:continue
        above=s["score"]>=threshold
        if above and not prev_above:
            if "open" not in df or not np.isfinite(df["open"].iloc[i+1]):continue
            entry=float(df["open"].iloc[i+1]);exit_=float(df["close"].iloc[i+hold_days])
            if entry<=0:continue
            window=df["close"].iloc[i+1:i+hold_days+1]
            levels=np.r_[entry,window.to_numpy()]
            drawdown=float(np.min(levels/np.maximum.accumulate(levels)-1))*100
            trades.append({
                "date":str(df.index[i].date()),"execution_date":str(df.index[i+1].date()),"entry":round(entry,2),"exit":round(exit_,2),
                "return_pct":round((exit_/entry-1)*100,2),
                "max_move_pct":round((float(window.max())/entry-1)*100,2),
                "max_drawdown_pct":round(drawdown,2),
                "score":s["score"]
            })
        prev_above=above
    vals=[t["return_pct"] for t in trades]
    return {
        "trades":trades,
        "count":len(trades),
        "win_rate":round(100*sum(v>0 for v in vals)/len(vals),1) if vals else None,
        "avg_return_pct":round(sum(vals)/len(vals),2) if vals else None,
        "median_return_pct":round(float(np.median(vals)),2) if vals else None,
        "avg_max_move_pct":round(sum(t["max_move_pct"] for t in trades)/len(trades),2) if trades else None,
        "avg_max_drawdown_pct":round(sum(t["max_drawdown_pct"] for t in trades)/len(trades),2) if trades else None,
        "hold_days":hold_days,"threshold":threshold,
        "caveats":["Price/volume indicators are recomputed point-in-time; fills use next-session open.","Universe is today's constituent set, so survivorship bias remains.","No fees, slippage, taxes or execution constraints."],
        "engine":"price_only_replay_v1"
    }
