
from __future__ import annotations
import math
import pandas as pd
import numpy as np

GRADE_BANDS = [
    (0.95, "A+"), (0.90, "A"), (0.80, "A-"), (0.70, "B+"), (0.60, "B"),
    (0.50, "B-"), (0.40, "C+"), (0.30, "C"), (0.20, "C-"), (0.10, "D"), (0.00, "F"),
]

def period_returns(close: pd.Series) -> dict:
    c = close.dropna()
    horizons = {"1W":5,"1M":21,"3M":63,"6M":126,"12M":252}
    out={}
    for label,n in horizons.items():
        out[label] = round((float(c.iloc[-1]/c.iloc[-1-n])-1)*100,2) if len(c)>n else None
    return out

def risk_metrics(df: pd.DataFrame) -> dict:
    c=df["close"].dropna()
    h=df["high"].reindex(c.index)
    l=df["low"].reindex(c.index)
    if len(c)<60:
        return {}
    prev=c.shift(1)
    tr=pd.concat([(h-l).abs(),(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    atr14=tr.rolling(14).mean().iloc[-1]
    ret=c.pct_change()
    vol20=float(ret.tail(20).std()*math.sqrt(252)*100)
    high52=float(c.tail(252).max()) if len(c)>=252 else float(c.max())
    dist52=(float(c.iloc[-1])/high52-1)*100
    last90=c.tail(90)
    rollmax=last90.cummax()
    dd=(last90/rollmax-1).min()*100
    return {
        "atr14_pct":round(float(atr14/c.iloc[-1]*100),2),
        "volatility20_ann_pct":round(vol20,2),
        "distance_52w_high_pct":round(dist52,2),
        "max_drawdown_90d_pct":round(float(dd),2),
    }

def warning_flags(rec: dict) -> list[dict]:
    flags=[]
    rs=rec.get("rs",{})
    px=rec.get("price",{})
    risk=rec.get("risk",{})
    vcp=rec.get("patterns",{}).get("vcp",{})
    stage=rec.get("stage",{}).get("value")
    if rs.get("quadrant")=="weakening":
        flags.append({"level":"medium","code":"RS_WEAKENING","text":"Relative strength is weakening"})
    if px.get("close") is not None and px.get("sma50") is not None and px["close"] < px["sma50"]:
        flags.append({"level":"medium","code":"BELOW_50DMA","text":"Price is below 50DMA"})
    d=vcp.get("distance_pct")
    if d is not None and d < -5:
        flags.append({"level":"high","code":"EXTENDED","text":"Price is extended beyond the detected pivot"})
    if stage==4:
        flags.append({"level":"high","code":"STAGE4","text":"Stage proxy is in decline"})
    if risk.get("atr14_pct",0) >= 5:
        flags.append({"level":"medium","code":"HIGH_ATR","text":"ATR% is elevated"})
    if risk.get("distance_52w_high_pct") is not None and risk["distance_52w_high_pct"] < -25:
        flags.append({"level":"medium","code":"FAR_FROM_HIGH","text":"More than 25% below 52-week high"})
    return flags

def _grade_from_percentile(p: float | None) -> str:
    if p is None or not np.isfinite(p): return "—"
    for cut,g in GRADE_BANDS:
        if p >= cut: return g
    return "F"

def assign_sector_factor_grades(records: list[dict]) -> None:
    """
    Our own peer-relative grades. Technical factors use 0-100 internal scores.
    Growth is only graded when the SEC/yahoo enrichment has a numeric value.
    """
    fields = {
        "RS": lambda x: x.get("rs",{}).get("score"),
        "Trend": lambda x: 100*x.get("trend_template",{}).get("passed",0)/max(x.get("trend_template",{}).get("total",8),1),
        "Setup": lambda x: x.get("scores",{}).get("setup"),
        "Volume": lambda x: x.get("scores",{}).get("radar",{}).get("Volume"),
        "Growth": lambda x: x.get("scores",{}).get("radar",{}).get("Growth") if (
            x.get("earnings",{}).get("eps_growth_yoy") is not None or x.get("earnings",{}).get("revenue_growth_yoy") is not None
        ) else None,
    }
    by_sector={}
    for r in records: by_sector.setdefault(r.get("sector","Unknown"),[]).append(r)

    for sector, arr in by_sector.items():
        for factor, getter in fields.items():
            vals=[(r,getter(r)) for r in arr]
            valid=[(r,float(v)) for r,v in vals if v is not None and np.isfinite(float(v))]
            valid.sort(key=lambda rv:rv[1])
            n=len(valid)
            pcts={}
            for i,(r,v) in enumerate(valid):
                pcts[r["ticker"]] = 1.0 if n==1 else i/(n-1)
            for r,_ in vals:
                r.setdefault("factor_grades",{})[factor]=_grade_from_percentile(pcts.get(r["ticker"]))
