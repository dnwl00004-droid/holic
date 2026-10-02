
from __future__ import annotations
import math

def _pv_enterprise_value(revenue, fcf_margin, growth, wacc=.10, terminal_growth=.025, years=5):
    if revenue is None or fcf_margin is None or revenue <= 0 or wacc <= terminal_growth:
        return None
    pv=0.0
    rev=float(revenue)
    for y in range(1,years+1):
        rev*=1+growth
        fcf=rev*fcf_margin
        pv += fcf/((1+wacc)**y)
    terminal_fcf=rev*fcf_margin*(1+terminal_growth)
    terminal=terminal_fcf/(wacc-terminal_growth)
    pv += terminal/((1+wacc)**years)
    return pv

def reverse_dcf_implied_growth(
    market_cap: float|None,
    net_debt: float|None,
    revenue: float|None,
    fcf_margin_pct: float|None,
    wacc: float=.10,
    terminal_growth: float=.025,
    years:int=5,
    lo:float=-.30,
    hi:float=.80
):
    """
    Back-solves the constant 5Y revenue growth rate that makes modeled EV equal current EV.
    FCF margin is held constant. This is deliberately simple and transparent.
    """
    if market_cap is None or net_debt is None or revenue is None or fcf_margin_pct is None:
        return {"available":False,"reason":"missing market cap, net debt, revenue, or FCF margin"}
    fcf_margin=float(fcf_margin_pct)/100.0
    if fcf_margin <= 0:
        return {"available":False,"reason":"non-positive FCF margin"}
    current_ev=float(market_cap)+(float(net_debt) if net_debt is not None else 0.0)
    if current_ev <= 0 or revenue <= 0:
        return {"available":False,"reason":"non-positive enterprise value or revenue"}

    def f(g):
        v=_pv_enterprise_value(revenue,fcf_margin,g,wacc,terminal_growth,years)
        return (v-current_ev) if v is not None else None

    flo,fhi=f(lo),f(hi)
    if flo is None or fhi is None:
        return {"available":False,"reason":"invalid DCF inputs"}
    if flo>0:
        implied=lo
        bounded=True
    elif fhi<0:
        implied=hi
        bounded=True
    else:
        a,b=lo,hi
        for _ in range(80):
            m=(a+b)/2
            fm=f(m)
            if abs(fm)<max(1,current_ev)*1e-8: break
            if fm>0:b=m
            else:a=m
        implied=(a+b)/2
        bounded=False

    # expectation load: implied growth vs simple recent actual sales growth if supplied later
    return {
        "available":True,
        "implied_revenue_growth_pct":round(implied*100,2),
        "market_cap":round(float(market_cap),0),
        "enterprise_value":round(current_ev,0),
        "revenue_base":round(float(revenue),0),
        "fcf_margin_pct":round(float(fcf_margin_pct),2),
        "wacc_pct":round(wacc*100,2),
        "terminal_growth_pct":round(terminal_growth*100,2),
        "forecast_years":years,
        "bounded_at_search_limit":bounded,
        "engine":"reverse_dcf_constant_margin_v1",
        "interpretation":"Growth rate implied by current enterprise value under the stated WACC, terminal growth and constant FCF margin."
    }

def dcf_sensitivity(revenue, fcf_margin_pct, net_debt, shares, growths=None, waccs=None, terminal_growth=.025, years=5):
    if None in (revenue,fcf_margin_pct,shares) or shares<=0:
        return {"available":False}
    growths=growths or [.00,.05,.10,.15,.20]
    waccs=waccs or [.08,.09,.10,.11,.12]
    margin=float(fcf_margin_pct)/100
    rows=[]
    for w in waccs:
        vals=[]
        for g in growths:
            ev=_pv_enterprise_value(revenue,margin,g,w,terminal_growth,years)
            equity=ev-(net_debt or 0) if ev is not None else None
            price=equity/shares if equity is not None else None
            vals.append(round(price,2) if price is not None and math.isfinite(price) else None)
        rows.append({"wacc_pct":round(w*100,1),"prices":vals})
    return {"available":True,"growths_pct":[round(x*100,1) for x in growths],"rows":rows}
