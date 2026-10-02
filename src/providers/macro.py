
from __future__ import annotations
import yfinance as yf

SERIES={
    "SPY":"S&P 500 ETF","^VIX":"VIX","^TNX":"US 10Y yield proxy",
    "DX-Y.NYB":"US Dollar Index","CL=F":"WTI crude","GC=F":"Gold","HG=F":"Copper",
    "BTC-USD":"Bitcoin","TLT":"20Y+ Treasury ETF","HYG":"High Yield ETF"
}
def macro_snapshot(period="6mo"):
    raw=yf.download(list(SERIES),period=period,interval="1d",auto_adjust=True,group_by="ticker",threads=True,progress=False)
    out={}
    for t,label in SERIES.items():
        try:
            d=raw[t].dropna(how="all")
            c=d["Close"] if "Close" in d.columns else d["close"]
            last=float(c.iloc[-1])
            r1=(last/float(c.iloc[-2])-1)*100 if len(c)>1 else None
            r21=(last/float(c.iloc[-22])-1)*100 if len(c)>22 else None
            out[t]={"label":label,"value":round(last,3),"change_1d_pct":round(r1,2) if r1 is not None else None,
                    "change_1m_pct":round(r21,2) if r21 is not None else None}
        except Exception:continue
    return out
