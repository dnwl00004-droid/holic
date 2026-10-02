
from __future__ import annotations
import numpy as np
import pandas as pd

CRISIS_WINDOWS={
    "COVID_CRASH":("2020-02-19","2020-03-23"),
    "2022_BEAR_LEG":("2022-01-03","2022-10-12"),
    "2023_BANK_STRESS":("2023-03-08","2023-03-20"),
}

def stress_returns(df:pd.DataFrame):
    c=df["close"].dropna()
    out={}
    for name,(a,b) in CRISIS_WINDOWS.items():
        w=c.loc[a:b]
        out[name]=round((float(w.iloc[-1]/w.iloc[0])-1)*100,2) if len(w)>=2 and (w.index[0]-pd.Timestamp(a)).days<=4 and (pd.Timestamp(b)-w.index[-1]).days<=4 else None
    return out

def correlation_and_risk(prices:dict[str,pd.Series],weights:dict[str,float]):
    joined=pd.concat([s.rename(t) for t,s in prices.items()],axis=1).dropna()
    if len(joined)<30:return {"available":False}
    rets=joined.pct_change().dropna()
    tickers=list(rets.columns)
    w=np.array([weights.get(t,0) for t in tickers],dtype=float)
    if w.sum()<=0:return {"available":False}
    w=w/w.sum()
    cov=rets.cov().to_numpy()*252
    corr=rets.corr().to_numpy()
    port_var=float(w@cov@w)
    port_vol=float(np.sqrt(max(port_var,0)))
    mrc=(cov@w)/port_vol if port_vol>0 else np.zeros_like(w)
    rc=w*mrc
    rc_pct=rc/rc.sum()*100 if abs(rc.sum())>1e-12 else np.zeros_like(rc)
    return {
        "available":True,
        "tickers":tickers,
        "correlation":[[round(float(x),3) for x in row] for row in corr],
        "annualized_vol_pct":round(port_vol*100,2),
        "risk_contribution_pct":{t:round(float(v),2) for t,v in zip(tickers,rc_pct)},
        "weights_pct":{t:round(float(v*100),2) for t,v in zip(tickers,w)},
    }

def hypothetical_stress(holdings:list[dict]):
    """
    Simple factor-free shocks using sector tags. Descriptive stress only.
    """
    scenarios={
        "MARKET_-10":{"market":-.10},
        "TECH_-20":{"market":-.05,"Technology":-.20,"Communication Services":-.12},
        "RATE_SHOCK":{"market":-.07,"Technology":-.12,"Financials":-.04,"Real Estate":-.15,"Utilities":-.10},
        "ENERGY_SPIKE":{"market":-.04,"Energy":.15,"Consumer Cyclical":-.08,"Industrials":-.05},
    }
    out={}
    total=sum(float(x.get("value",0)) for x in holdings) or 1
    for name,shocks in scenarios.items():
        pnl=0
        for h in holdings:
            sec=h.get("sector")
            shock=shocks.get(sec,shocks.get("market",0))
            pnl+=float(h.get("value",0))*shock
        out[name]={"impact_pct":round(pnl/total*100,2),"impact_value":round(pnl,2)}
    return out
