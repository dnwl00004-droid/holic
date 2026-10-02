
from __future__ import annotations
import numpy as np
import pandas as pd

def rsi14(close: pd.Series) -> float | None:
    c=close.dropna()
    if len(c)<20: return None
    d=c.diff()
    gain=d.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-d.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rs=gain/max(float(loss.iloc[-1]),1e-12)
    return round(float(100-100/(1+rs)),2)

def obv_series(df: pd.DataFrame) -> pd.Series:
    d=df.dropna(subset=["close","volume"]).copy()
    direction=np.sign(d["close"].diff()).fillna(0)
    return (direction*d["volume"]).cumsum()

def divergence_proxy(df: pd.DataFrame, lookback: int=30) -> dict:
    d=df.dropna(subset=["close","volume"]).tail(max(lookback+10,50))
    if len(d)<35: return {"rsi":"none","obv":"none"}
    c=d["close"]
    # RSI series
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rsi=100-100/(1+gain/loss.replace(0,np.nan))
    obv=obv_series(d)

    def slope(s):
        s=s.dropna().tail(lookback)
        if len(s)<10:return 0
        x=np.arange(len(s),dtype=float)
        return float(np.polyfit(x,s.to_numpy(dtype=float),1)[0])

    ps=slope(c); rs=slope(rsi); os=slope(obv)
    rsi_div = "bullish" if ps<0 and rs>0 else "bearish" if ps>0 and rs<0 else "none"
    obv_div = "bullish" if ps<0 and os>0 else "bearish" if ps>0 and os<0 else "confirming" if ps*os>0 else "none"
    return {"rsi":rsi_div,"obv":obv_div}

def exhaustion_9_proxy(close: pd.Series) -> dict:
    """
    Transparent 9-bar exhaustion proxy:
    counts consecutive closes > or < close four sessions earlier.
    This is not presented as an official DeMark indicator.
    """
    c=close.dropna()
    up=down=0
    for i in range(max(4,len(c)-20),len(c)):
        if i<4: continue
        if c.iloc[i] > c.iloc[i-4]:
            up += 1; down=0
        elif c.iloc[i] < c.iloc[i-4]:
            down += 1; up=0
        else:
            up=down=0
    return {
        "direction":"up" if up else ("down" if down else "none"),
        "count":int(max(up,down)),
        "complete":bool(max(up,down)>=9),
        "engine":"9bar_exhaustion_proxy_v1"
    }

def volume_breakthrough(df: pd.DataFrame) -> dict:
    d=df.dropna(subset=["close","volume"])
    if len(d)<30:return {"detected":False}
    rel=float(d["volume"].iloc[-1]/max(d["volume"].iloc[-21:-1].mean(),1))
    ret=float(d["close"].iloc[-1]/d["close"].iloc[-2]-1)
    detected=rel>=1.5 and ret>=.02
    return {"detected":bool(detected),"relative_volume":round(rel,2),"day_return_pct":round(ret*100,2)}

def entry_timing_score(df: pd.DataFrame, vcp: dict) -> dict:
    """
    Separates chart/setup quality from entry timing.
    Rewards proximity to pivot, 20/50DMA support, controlled ATR extension and volume behavior.
    """
    d=df.dropna(subset=["close","high","low","volume"])
    if len(d)<60:return {"score":None,"label":"UNKNOWN"}
    c=d["close"]; px=float(c.iloc[-1])
    ma20=float(c.tail(20).mean()); ma50=float(c.tail(50).mean())
    prev=c.shift(1)
    tr=pd.concat([(d["high"]-d["low"]).abs(),(d["high"]-prev).abs(),(d["low"]-prev).abs()],axis=1).max(axis=1)
    atr=float(tr.tail(14).mean())
    ext=(px-ma20)/max(atr,1e-9)
    dist=vcp.get("distance_pct")
    rv=float(d["volume"].iloc[-1]/max(d["volume"].iloc[-21:-1].mean(),1))

    pivot_score=25
    if dist is not None:
        if -1.5 <= dist <= 2.5: pivot_score=45
        elif 2.5 < dist <= 6: pivot_score=38
        elif 6 < dist <= 10: pivot_score=28
        elif -5 <= dist < -1.5: pivot_score=20
        else: pivot_score=5
    support=25 if px>=ma20>=ma50 else 18 if px>=ma50 else 5
    extension=max(0,20-abs(ext-1.0)*5)
    volume=max(0,min(10, 5+(rv-1)*5))
    score=int(round(max(0,min(100,pivot_score+support+extension+volume))))
    label="READY" if score>=78 else "NEAR" if score>=65 else "WAIT" if score>=45 else "EXTENDED_OR_WEAK"
    return {"score":score,"label":label,"atr_extension":round(ext,2),"relative_volume":round(rv,2),"engine":"entry_timing_v1"}
